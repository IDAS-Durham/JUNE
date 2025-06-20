import logging
import datetime
import yaml
import numpy as np
from typing import Optional, List
from pathlib import Path
from time import perf_counter
from time import time as wall_clock

from june import paths
from june.activity import ActivityManager
from june.exc import SimulatorError
from june.global_context import GlobalContext
from june.groups.leisure import Leisure
from june.groups.travel import Travel
from june.groups.contact import ContactManager
from june.epidemiology.epidemiology import Epidemiology
from june.interaction import Interaction
from june.records.event_recording import TTEventRecorder, print_tt_simulation_report
from june.tracker import Tracker
from june.policy import Policies
from june.event import Events
from june.time import Timer
from june.records import Record
from june.world import World
from june.mpi_wrapper import mpi_rank, mpi_comm, mpi_size, mpi_available

# Import ZoonoticTransmission for handling rat-human disease transmission
try:
    from june.zoonosis.zoonotic_transmission import ZoonoticTransmission
except ImportError:
    ZoonoticTransmission = None

default_config_filename = paths.configs_path / "config_simulation.yaml"

output_logger = logging.getLogger("simulator")
mpi_logger = logging.getLogger("mpi")
rank_logger = logging.getLogger("rank")
mpi_logger.propagate = False
if mpi_rank > 0:
    output_logger.propagate = False
    mpi_logger.propagate = False


def enable_mpi_debug(results_folder):
    from june.logging import MPIFileHandler

    logging_file = Path(results_folder) / "mpi.log"
    with open(logging_file, "w"):
        pass
    mh = MPIFileHandler(logging_file)
    rank_logger.addHandler(mh)


def _read_checkpoint_dates_from_file(config_filename):
    with open(config_filename) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return _read_checkpoint_dates(config.get("checkpoint_save_dates", None))


def _read_checkpoint_dates(checkpoint_dates):
    if isinstance(checkpoint_dates, datetime.date):
        return (checkpoint_dates,)
    elif type(checkpoint_dates) == str:
        return (datetime.datetime.strptime(checkpoint_dates, "%Y-%m-%d"),)
    elif type(checkpoint_dates) in [list, tuple]:
        ret = []
        for date in checkpoint_dates:
            if type(date) == str:
                dd = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            else:
                dd = date
            ret.append(dd)
        return tuple(ret)
    else:
        return ()


class Simulator:
    ActivityManager = ActivityManager

    def __init__(
        self,
        world: World,
        interaction: Interaction,
        timer: Timer,
        activity_manager: ActivityManager,
        epidemiology: Epidemiology,
        tracker: Tracker,
        events: Optional[Events] = None,
        record: Optional[Record] = None,
        checkpoint_save_dates: List[datetime.date] = None,
        checkpoint_save_path: str = None,
        feature_flags: Optional[dict] = None
    ):
        """
        Class to run an epidemic spread simulation on the world.
        """
        # Process feature flags with defaults
        if feature_flags is None:
            feature_flags = {}
        
        self.friend_hangouts_enabled = feature_flags.get("friend_hangouts_enabled", False)
        self.test_and_trace_enabled = feature_flags.get("test_and_trace_enabled", False)
        self.ratty_dynamics_enabled = feature_flags.get("ratty_dynamics_enabled", False)
        self.rat_animations_enabled = feature_flags.get("rat_animations_enabled", False)
        
        # Original initialization code
        self.activity_manager = activity_manager
        self.world = world
        self.interaction = interaction
        self.events = events
        self.timer = timer
        self.epidemiology = epidemiology
        
        if self.epidemiology:
            self.epidemiology.set_medical_care(
                world=world, activity_manager=activity_manager
            )
            self.epidemiology.set_immunity(self.world)
            self.epidemiology.set_past_vaccinations(
                people=self.world.people, date=self.timer.date, record=record
            )

        self.tracker = tracker
        if self.events is not None:
            self.events.init_events(world=world)
            
        self.checkpoint_save_dates = _read_checkpoint_dates(checkpoint_save_dates)
        if self.checkpoint_save_dates:
            if not checkpoint_save_path:
                checkpoint_save_path = "results/checkpoints"
            self.checkpoint_save_path = Path(checkpoint_save_path)
            self.checkpoint_save_path.mkdir(parents=True, exist_ok=True)
        
        self.record = record
        if self.record is not None and self.record.record_static_data:
            self.record.static_data(world=world)
        
        # Only initialize rat manager if feature is enabled
        self.rat_manager = None
        self.produce_rat_animations = False

        if self.ratty_dynamics_enabled:
            output_logger.info("Ratty dynamics enabled, initializing rat manager")
            try:
                from june.zoonosis.rat_manager import RatManager
                self.rat_manager = RatManager(world=world)
                self.produce_rat_animations = self.rat_animations_enabled
                output_logger.info(f"Rat animations: {self.produce_rat_animations}")
            except ImportError as e:
                output_logger.warning(f"Failed to import RatManager: {e}")
                output_logger.warning("Continuing without rat dynamics")
        
        # Only initialize contact manager if test and trace is enabled
        self.contact_manager = None
        if self.test_and_trace_enabled:
            output_logger.info("Test and Trace enabled, initialising contact manager")
            self.contact_manager = ContactManager(self)
            
            # Configure the contact retention based on policy settings            
            disease_config = None
            
            disease_config = GlobalContext.get_disease_config()
            output_logger.info("Using disease_config from GlobalContext")
                    
            # Use disease_config if available
            if disease_config is not None:
                tracing_data = disease_config.policy_manager.get_policy_data("tracing")
                self.contact_retention_days = tracing_data.get("contact_retention_days", 14)
                output_logger.info(f"Using contact retention days from config: {self.contact_retention_days}")
            
            # Connect contact manager to leisure system if it exists
            if hasattr(self.activity_manager, 'leisure') and self.activity_manager.leisure is not None:
                output_logger.info("Connecting contact manager to leisure system")
                self.activity_manager.leisure.set_contact_manager(self.contact_manager)
        else:
            output_logger.info("Test and Trace disabled, skipping contact manager initialization")
            
        # Initialize zoonotic transmission if rat_manager is properly initialized and feature is enabled
        self.zoonotic_transmission = None
        if self.ratty_dynamics_enabled and self.rat_manager is not None and ZoonoticTransmission is not None:
            try:
                output_logger.info("Initializing zoonotic transmission module")
                self.zoonotic_transmission = ZoonoticTransmission(rat_manager=self.rat_manager)
                output_logger.info("Zoonotic transmission module initialized successfully")
            except Exception as e:
                output_logger.warning(f"Failed to initialize zoonotic transmission: {e}")
                output_logger.warning("Continuing without zoonotic transmission")

    @classmethod
    def from_file(
        cls,
        world: World,
        interaction: Interaction,
        policies: Optional[Policies] = None,
        events: Optional[Events] = None,
        epidemiology: Optional[Epidemiology] = None,
        tracker: Optional[Tracker] = None,
        leisure: Optional[Leisure] = None,
        travel: Optional[Travel] = None,
        config_filename: str = default_config_filename,
        checkpoint_save_path: str = None,
        record: Optional[Record] = None,
    ) -> "Simulator":
        """
        Load config for simulator from world.yaml
        """
        # Load the configuration file to get feature flags
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        
        # Extract feature flags with defaults in case they're not in the config
        features = config.get("features", {})

        #Friendship networks
        friend_hangouts_config = features.get("friend_hangouts", {"enabled": False})
        friend_hangouts_enabled = friend_hangouts_config.get("enabled", False)
        
        # Test and trace settings
        test_and_trace_config = features.get("test_and_trace", {"enabled": False})
        test_and_trace_enabled = test_and_trace_config.get("enabled", False)
        
        # Ratty dynamics settings
        ratty_dynamics_config = features.get("ratty_dynamics", {"enabled": False})
        ratty_dynamics_enabled = ratty_dynamics_config.get("enabled", False)
        rat_animations_enabled = ratty_dynamics_config.get("animations", False)

        
        output_logger.info(f"Feature flags from config: Friend hangouts: {friend_hangouts_enabled}, "
                        f"Test and Trace: {test_and_trace_enabled}, "
                        f"Ratty Dynamics: {ratty_dynamics_enabled}, "
                        f"Rat Animations: {rat_animations_enabled}, ")
        
        # Continue with original method
        checkpoint_save_dates = _read_checkpoint_dates_from_file(config_filename)
        timer = Timer.from_file(config_filename=config_filename)
        activity_manager = cls.ActivityManager.from_file(
            config_filename=config_filename,
            world=world,
            leisure=leisure,
            travel=travel,
            policies=policies,
            timer=timer,
            record=record,
        )
        
        # Store feature flags to pass to the constructor
        feature_flags = {
            "friend_hangouts_enabled": friend_hangouts_enabled,
            "test_and_trace_enabled": test_and_trace_enabled,
            "ratty_dynamics_enabled": ratty_dynamics_enabled,
            "rat_animations_enabled": rat_animations_enabled
        }

        simulator = cls(
            world=world,
            interaction=interaction,
            timer=timer,
            events=events,
            activity_manager=activity_manager,
            epidemiology=epidemiology,
            tracker=tracker,
            record=record,
            checkpoint_save_dates=checkpoint_save_dates,
            checkpoint_save_path=checkpoint_save_path,
            feature_flags=feature_flags
        )

        return simulator

    @classmethod
    def from_checkpoint(
        cls,
        world: World,
        checkpoint_load_path: str,
        interaction: Interaction,
        epidemiology: Optional[Epidemiology] = None,
        tracker: Optional[Tracker] = None,
        policies: Optional[Policies] = None,
        leisure: Optional[Leisure] = None,
        travel: Optional[Travel] = None,
        config_filename: str = default_config_filename,
        record: Optional[Record] = None,
        events: Optional[Events] = None,
        reset_infections=False,
    ):
        from june.hdf5_savers.checkpoint_saver import generate_simulator_from_checkpoint

        return generate_simulator_from_checkpoint(
            world=world,
            checkpoint_path=checkpoint_load_path,
            interaction=interaction,
            policies=policies,
            epidemiology=epidemiology,
            tracker=tracker,
            leisure=leisure,
            travel=travel,
            config_filename=config_filename,
            record=record,
            events=events,
            reset_infections=reset_infections,
        )

    def clear_world(self):
        """
        Removes everyone from all possible groups, sets everyone's busy attribute
        to False, and cleans up skinny persons that have moved back home.
        """
        # Clear all groups first
        for super_group_name in self.activity_manager.all_super_groups:
            if "visits" in super_group_name:
                continue
            try:
                grouptype = getattr(self.world, super_group_name, None)
                if grouptype is not None:
                    for group in grouptype.members:
                        group.clear()
            except AttributeError:
                # If the attribute doesn't exist, just continue
                continue

        # Reset busy flags and leisure subgroups
        for person in self.world.people.members:            
            person.busy = False
            person.subgroups.leisure = None
        
        # Clean up skinny persons
        from june.demography import Person
        to_remove = []
        
        # Find all skinny persons (persons not on their home rank)
        for person_id, person in list(Person._persons.items()):
            if hasattr(person, '_current_rank') and person._current_rank != mpi_rank:
                to_remove.append(person_id)
        
        # Remove all identified skinny persons
        for person_id in to_remove:
            if person_id in Person._persons:
                del Person._persons[person_id]
        
        # Synchronize removal across ranks
        mpi_comm.Barrier()
        

    def do_timestep(self):
        """
        Perform a time step in the simulation. First, ActivityManager is called
        to send people to the corresponding subgroups according to the current daytime.
        Then we iterate over all the groups and create an InteractiveGroup object, which
        extracts the relevant information of each group to carry the interaction in it.
        We then pass the interactive group to the interaction module, which returns the ids
        of the people who got infected. We record the infection locations, update the health
        status of the population, and distribute scores among the infectors to calculate R0.
        """
        output_logger.info("==================== timestep ====================")
        tick_s, tickw_s = perf_counter(), wall_clock()
        tick, tickw = perf_counter(), wall_clock()

        if self.activity_manager.policies is not None:
            self.activity_manager.policies.interaction_policies.apply(
                date=self.timer.date, interaction=self.interaction
            )
            self.activity_manager.policies.regional_compliance.apply(
                date=self.timer.date, regions=self.world.regions
            )
        activities = self.timer.activities
        # apply events
        if self.events is not None:
            self.events.apply(
                date=self.timer.date,
                world=self.world,
                activities=activities,
                day_type=self.timer.day_type,
                simulator=self,
            )
        if not activities or len(activities) == 0:
            output_logger.info("==== do_timestep(): no active groups found. ====")
            return

        print("======DO_TIMESTEP ACTIVITY MANAGER=======")

        (
            people_from_abroad_dict,
            n_people_from_abroad,
            n_people_going_abroad,
            to_send_abroad,  # useful for knowing who's MPI-ing, so can send extra info as needed.
        ) = self.activity_manager.do_timestep(record=self.record)
        tick_interaction = perf_counter()
        print("=========DO_TIMESTEP ACTIVITY MANAGER FINISHED =========")

        

        # Set current time on interaction object for isolation checks
        if self.interaction:
            self.interaction.current_time = self.timer.now
            
        # get the supergroup instances that are active in this time step:
        active_super_groups = self.activity_manager.active_super_groups
        super_group_instances = []
        for super_group_name in active_super_groups:
            if "visits" not in super_group_name:
                try:
                    super_group_instance = getattr(self.world, super_group_name, None)
                    if super_group_instance is not None and len(super_group_instance) > 0:
                        super_group_instances.append(super_group_instance)
                except (AttributeError, TypeError) as e:
                    output_logger.warning(f"Could not access supergroup {super_group_name}: {e}")
                    continue

        # Log the final list of super group instances
        print("\n=== Super Group Instances ===")
        for idx, instance in enumerate(super_group_instances, start=1):
            print(f"Instance {idx}: {repr(instance)}")

        # Initialize counters for people tracking
        initial_people = len(self.world.people)  # People before movement
        n_cemetery = sum(len(cemetery.people) for cemetery in self.world.cemeteries.members)
        
        # Track infections
        infected_ids = []  # ids of the newly infected people
        infection_ids = []  # ids of the viruses they got

        print(
            f"Info for rank {mpi_rank}, "
            f"Date = {self.timer.date}, "
            f"number of deaths = {n_cemetery}, "
            f"number of infected = {len(self.world.people.infected)}"
        )

        print("\n=== Processing Super Group Instances ===")
        
        print(f"[Rank {mpi_rank}] Simulator: Starting timestep for {self.timer.date}")
        
        # Process groups for infections only
        for super_group in super_group_instances:
            for group in super_group:
                if group.external:
                    continue
                
                # Get people from abroad for this group
                people_from_abroad = people_from_abroad_dict.get(
                    group.spec, {}
                ).get(group.id, None)
                
                # Only track new infections, ignore group size
                new_infected, new_infections, _ = self.interaction.time_step_for_group(
                    group=group,
                    people_from_abroad=people_from_abroad,
                    delta_time=self.timer.duration,
                    record=self.record,
                )

                infected_ids.extend(new_infected)
                infection_ids.extend(new_infections)
        

        if self.interaction and hasattr(self.interaction, '_receive_infection_records'):
            self.interaction._receive_infection_records(self.record)

        mpi_comm.Barrier()
        
        # Calculate final people count after movement
        final_people = len(self.world.people)  # People after movement
        
        print("\n=== Interaction Summary ===")
        print(f"Initial People in World: {initial_people}")
        print(f"Final People in World: {final_people}")
        print(f"Deaths: {n_cemetery}")
        print(f"People From Abroad: {n_people_from_abroad}")
        print(f"People Going Abroad: {n_people_going_abroad}")
        print(f"People Movement Delta: {final_people - initial_people}")
        print(f"New Infections: {len(infected_ids)}")

        tock_interaction = perf_counter()
        rank_logger.info(
            f"Rank {mpi_rank} -- interaction -- {tock_interaction-tick_interaction}"
        )

        tick_tracker = perf_counter()
        # Loop in here
        if isinstance(self.tracker, type(None)):
            pass
        else:
            self.tracker.trackertimestep(
                self.activity_manager.all_super_groups, self.timer
            )
        tock_tracker = perf_counter()
        rank_logger.info(f"Rank {mpi_rank} -- tracker -- {tock_tracker-tick_tracker}")

        self.epidemiology.do_timestep(
            simulator=self,
            world=self.world,
            timer=self.timer,
            record=self.record,
            infected_ids=infected_ids,
            infection_ids=infection_ids,
            people_from_abroad_dict=people_from_abroad_dict
        )
        
        self.interaction.print_transmission_statistics()

        current_date = self.timer.date
        next_step_date = current_date + datetime.timedelta(hours=self.timer.shift_duration)
        is_end_of_day = current_date.day != next_step_date.day  # Day changes on next step
        
        # Clean old contacts at the end of the day
        if is_end_of_day and self.test_and_trace_enabled and self.contact_manager is not None:
            
            self.contact_manager.process_test_results(self.timer.now)
            
            mpi_comm.Barrier()    

            output_logger.info("Cleaning old contacts in the contact manager")
            output_logger.info(f"Current simulation day (fractional): {self.timer.now}")
            self.contact_manager.clean_old_contacts(
                current_timestamp=self.timer.now,
                days_to_remember=self.contact_retention_days,
                force=True
            )

        # Add rat simulation step
        if self.rat_manager is not None and is_end_of_day:
            print("\n=== Running Rat Disease Simulation Step ===")
            # Pass the current time step duration to the rat_manager
            rat_results = self.rat_manager.time_step(1)
            
            # Optionally log some results
            print(f"Number of Rats: {self.rat_manager.num_rats}"),
            print(f"Rat infections: {rat_results['infected']}")
            print(f"Rats with high immunity: {rat_results['immunity_08']}")
            print(f"Rats with medium immunity: {rat_results['immunity_05']}")

            if self.epidemiology is not None and self.zoonotic_transmission is not None:
                print("\n=== Processing Rat-to-Human Transmissions ===")
                
                # Use the zoonotic transmission module instead
                human_infections = self.zoonotic_transmission.process_rat_to_human_infections(
                    world=self.world,
                    timer=self.timer,
                    epidemiology=self.epidemiology,
                    record=self.record,
                    duration=1.0  # Full day duration (24 hours)
                )
                print(f"New human infections from rats: {human_infections}")

                human2ratinfections = self.zoonotic_transmission.process_human_to_rat_infections(
                    world=self.world, 
                    timer=self.timer,
                    epidemiology=self.epidemiology,
                    record=self.record,
                    duration=1.0
                )
                print(f"New rat infections from humans: {human2ratinfections}")

            # Save a visualisation frame for this day (but only on rank 0 for MPI)
            if mpi_rank == 0 and self.produce_rat_animations:
                if not hasattr(self.rat_manager, 'viz_frame_count'):
                    self.rat_manager.rat_visualisation.initialise_visualisation_tracker()
                
                # Save the current state as a frame
                self.rat_manager.rat_visualisation.save_geo_sections_frame(date=current_date)

        tick, tickw = perf_counter(), wall_clock()
        mpi_comm.Barrier()
        tock, tockw = perf_counter(), wall_clock()
        rank_logger.info(f"Rank {mpi_rank} -- interaction_waiting -- {tock-tick}")

        # Ensure all ranks have finished processing
        mpi_comm.Barrier()
        
        # Gather detailed counts from all ranks
        local_counts = (
            initial_people,  # Initial people count
            final_people,    # Final people count
            n_people_from_abroad,
            n_people_going_abroad
        )
        all_counts = mpi_comm.allgather(local_counts)
        
        # Calculate global totals
        total_initial = sum(c[0] for c in all_counts)
        total_final = sum(c[1] for c in all_counts)
        total_from_abroad = sum(c[2] for c in all_counts)
        total_going_abroad = sum(c[3] for c in all_counts)
        
        # Verify global conservation of people
        if total_initial != total_final:
            movement_delta = total_final - total_initial
            abroad_delta = total_from_abroad - total_going_abroad
            raise SimulatorError(
                f"Global people conservation error on rank {mpi_rank}:\n"
                f"Total initial people: {total_initial}\n"
                f"Total final people: {total_final}\n"
                f"Net change in people: {movement_delta}\n"
                f"Expected net change (from_abroad - going_abroad): {abroad_delta}\n"
                f"Discrepancy: {movement_delta - abroad_delta}\n"
                f"Movement details:\n"
                f"- Total from abroad: {total_from_abroad}\n"
                f"- Total going abroad: {total_going_abroad}\n"
                f"Local counts on this rank:\n"
                f"- Initial people: {initial_people}\n"
                f"- Final people: {final_people}\n"
                f"- From abroad: {n_people_from_abroad}\n"
                f"- Going abroad: {n_people_going_abroad}\n"
                f"- Net movement: {final_people - initial_people}"
            )
        
        if self.test_and_trace_enabled:
            #from june.records.event_recording import are_test_and_trace_policies_active
            #if are_test_and_trace_policies_active():
                #print_tt_simulation_report(days_simulated=self.timer.total_days)
            tt_recorder = GlobalContext.get_tt_event_recorder()
            if tt_recorder:
                tt_recorder.time_step(self.timer.now)


        # remove everyone from their active groups
        self.clear_world()
        
        tock, tockw = perf_counter(), wall_clock()
        output_logger.info(
            f"CMS: Timestep for rank {mpi_rank}/{mpi_size} - {tock - tick_s},"
            f"{tockw-tickw_s} - {self.timer.date}\n"
        )
        mpi_logger.info(f"{self.timer.date},{mpi_rank},timestep,{tock-tick_s}")

    def run(self):
        """
        Run simulation with n_seed initial infections
        """
        
        output_logger.info(
            f"Starting simulation for {self.timer.total_days} days at day {self.timer.date},"
            f"to run for {self.timer.total_days} days"
        )

        if self.test_and_trace_enabled:
            output_logger.info("Test and Trace enabled, initializing TTEventRecorder")
            tt_recorder = TTEventRecorder()
            GlobalContext.set_tt_event_recorder(tt_recorder)
            self.update_registered_members_home_ranks()

        else:
            output_logger.info("Test and Trace disabled, skipping TTEventRecorder")
            GlobalContext.set_tt_event_recorder(None)

        GlobalContext.set_simulator(self)

        # Update friend home ranks after domain splitting
        if self.friend_hangouts_enabled:
            self.update_friends_home_ranks()
            mpi_comm.Barrier()

        self.clear_world()

        if self.record is not None:
            try:
                self.record.parameters(
                    interaction=self.interaction,
                    epidemiology=self.epidemiology,
                    activity_manager=self.activity_manager,
                )
            except Exception as e:
                output_logger.error(f"Error recording parameters: {e}")

        #START OF THE SIMULATION LOOP
        while self.timer.date < self.timer.final_date:
            if self.epidemiology:
                self.epidemiology.infection_seeds_timestep(
                    self.timer, record=self.record
                )
                # Update interaction with any new initial infected IDs after seeding
                if hasattr(self.interaction, 'update_initial_infected_ids'):
                    self.interaction.update_initial_infected_ids()
            mpi_comm.Barrier()
            if mpi_rank == 0:
                rank_logger.info("Next timestep")
            self.do_timestep()
                
            if (
                self.timer.date.date() in self.checkpoint_save_dates
                and (self.timer.now + self.timer.duration).is_integer()
            ):  # this saves in the last time step of the day
                saving_date = self.timer.date.date()
                # we can resume consistenly
                output_logger.info(
                    f"Saving simulation checkpoint at {self.timer.date.date()}"
                )
                self.save_checkpoint(saving_date)
            next(self.timer)
        
        # Create animation from saved frames (only on rank 0)
        if mpi_rank == 0 and self.rat_manager is not None and self.produce_rat_animations:
            animation_paths = self.rat_manager.rat_visualisation.compile_geo_sections_animations(
                output_dir="outputs/rat_animations"
            )
            
            for section_id, path in animation_paths.items():
                print(f"Animation for section {section_id} saved to: {path}")

        if self.record:
            self.record.combine_outputs()
        
        if self.test_and_trace_enabled:
            from june.records.event_recording import export_simulation_results
            export_simulation_results(output_dir="./results")
        

    def update_registered_members_home_ranks(self):
        """
        For each group type (companies, care homes, schools, universities),
        update the registered_members_ids to include the rank where each member lives.
        
        Works in both MPI and non-MPI environments:
        - In MPI mode: Ranks collaborate to find member home ranks
        - In non-MPI mode: All members are assigned to rank 0
        """
        
        if mpi_available:
            print(f"Updating registered members home ranks on rank {mpi_rank}")
        else:
            print("Updating registered members home ranks (non-MPI mode)")
        
        # Group types to check
        group_types = [
            ("companies", "Company"), 
            ("care_homes", "CareHome"), 
            ("schools", "School"),
            ("universities", "University")
        ]
        
        # Step 1: Collect all member IDs from groups on this rank
        all_member_ids = set()
        groups_with_members = []
        
        for group_type_name, _ in group_types:
            group_type = getattr(self.world, group_type_name, None)
            if group_type is None or not hasattr(group_type, "members"):
                continue
                    
            for group in group_type.members:
                if not hasattr(group, "registered_members_ids"):
                    continue
                        
                for subgroup_id, member_ids in group.registered_members_ids.items():
                    for i, member_info in enumerate(member_ids):
                        # Extract the member ID (handle both plain IDs and tuples)
                        if isinstance(member_info, tuple) and len(member_info) == 2:
                            member_id = member_info[0]
                        else:
                            member_id = member_info
                                
                        all_member_ids.add(member_id)
                            
                # Track groups for later updating
                groups_with_members.append((group_type_name, group))
        
        # Convert to a sorted list for consistent ordering
        all_member_ids = sorted(list(all_member_ids))
        
        from june.demography.person import Person
        
        # Different logic for MPI vs non-MPI
        if mpi_available:
            # MPI mode: Distributed ID lookup
            
            # Step 2: Check which IDs exist on this rank
            local_id_to_rank = {}
            unknown_ids = []
            
            for member_id in all_member_ids:
                person = Person.find_by_id(member_id)
                if person is not None:
                    # Found locally
                    local_id_to_rank[member_id] = mpi_rank
                else:
                    # Not found locally - add to list of IDs to query other ranks
                    unknown_ids.append(member_id)
            
            # Step 3: Share only the unknown IDs with other ranks
            all_unknown_ids = mpi_comm.allgather(unknown_ids)
            
            # Step 4: Check if any of the IDs from other ranks exist on this rank
            additional_mappings = {}
            
            for rank, rank_unknown_ids in enumerate(all_unknown_ids):
                if rank == mpi_rank:
                    # Skip our own unknown IDs
                    continue
                        
                for member_id in rank_unknown_ids:
                    person = Person.find_by_id(member_id)
                    if person is not None:
                        # We found an ID that another rank was looking for
                        additional_mappings[member_id] = mpi_rank
            
            # Step 5: Share these additional mappings
            all_additional_mappings = mpi_comm.allgather(additional_mappings)
            
            # Build the global ID-to-rank mapping
            global_id_to_rank = {}
            # Add our local findings first
            global_id_to_rank.update(local_id_to_rank)
            
            # Add additional mappings from all ranks
            for rank_mappings in all_additional_mappings:
                global_id_to_rank.update(rank_mappings)
            
        else:
            # Non-MPI mode: All IDs are on rank 0
            global_id_to_rank = {member_id: 0 for member_id in all_member_ids}
        
        # Step 6: Update all groups with the correct home rank information
        for group_type_name, group in groups_with_members:
            for subgroup_id, member_ids in list(group.registered_members_ids.items()):
                updated_member_ids = []
                
                for member_info in member_ids:
                    # Extract the member ID (handle both plain IDs and tuples)
                    if isinstance(member_info, tuple) and len(member_info) == 2:
                        member_id = member_info[0]
                    else:
                        member_id = member_info
                    
                    # Get the home rank from the global mapping
                    home_rank = global_id_to_rank.get(member_id)
                    
                    if home_rank is not None:
                        # Add to the updated list
                        updated_member_ids.append((member_id, home_rank))
                    else:
                        # ID not found in any rank, use default of 0
                        # This should not happen if everything is working correctly
                        updated_member_ids.append((member_id, 0))
                
                # Replace the old list with the updated one
                group.registered_members_ids[subgroup_id] = updated_member_ids
        
        # Ensure all ranks are synchronized in MPI mode
        mpi_comm.Barrier()

    def update_friends_home_ranks(self):
        """
        Update the home rank for each person's friends after domain splitting.
        Replaces the default home rank (0) with the actual home rank where each friend resides.
        
        Works in both MPI and non-MPI environments:
        - In MPI mode: Ranks collaborate to find friend home ranks
        - In non-MPI mode: All friends are assigned to rank 0
        """
        
        if not mpi_available:
            return
        
        # Step 1: Collect all friend IDs from people on this rank
        all_friend_ids = set()
        people_with_friends = []
        
        for person in self.world.people.members:
            if hasattr(person, 'friends') and person.friends:
                # Handle both old format (just home_rank) and new format (dict)
                for friend_id, friend_data in person.friends.items():
                    all_friend_ids.add(friend_id)
                people_with_friends.append(person)
        
        # Convert to sorted list for consistent ordering
        all_friend_ids = sorted(list(all_friend_ids))
        
        from june.demography.person import Person
                        
        # Step 2: Check which friend IDs exist on this rank
        local_id_to_rank = {}
        unknown_ids = []
        
        for friend_id in all_friend_ids:
            person = Person.find_by_id(friend_id)
            if person is not None:
                # Found locally - store their home rank
                local_id_to_rank[friend_id] = getattr(person, '_home_rank', mpi_rank)
            else:
                # Not found locally - add to list of IDs to query other ranks
                unknown_ids.append(friend_id)
        
        # Step 3: Share unknown IDs with other ranks
        all_unknown_ids = mpi_comm.allgather(unknown_ids)
        
        # Step 4: Check if any of the IDs from other ranks exist on this rank
        additional_mappings = {}
        
        for rank, rank_unknown_ids in enumerate(all_unknown_ids):
            if rank == mpi_rank:
                # Skip our own unknown IDs
                continue
                    
            for friend_id in rank_unknown_ids:
                person = Person.find_by_id(friend_id)
                if person is not None:
                    # Found a friend that another rank was looking for
                    additional_mappings[friend_id] = getattr(person, '_home_rank', mpi_rank)
        
        # Step 5: Share these additional mappings
        all_additional_mappings = mpi_comm.allgather(additional_mappings)
        
        # Build the global friend_id-to-home_rank mapping
        global_friend_to_home_rank = {}
        # Add our local findings first
        global_friend_to_home_rank.update(local_id_to_rank)
        
        # Add additional mappings from all ranks
        for rank_mappings in all_additional_mappings:
            global_friend_to_home_rank.update(rank_mappings)
        
        # Step 6: Update each person's friends dictionary with correct home ranks
        updated_people = 0
        updated_friends = 0
        
        for person in people_with_friends:
            person_updated = False
            
            # Create a new friends dictionary with updated home ranks
            updated_friends_dict = {}
            
            for friend_id, friend_data in person.friends.items():
                # Handle both old format (just home_rank) and new format (dict)
                if isinstance(friend_data, dict):
                    # New format - update home_rank, keep hobbies
                    current_home_rank = friend_data.get("home_rank", 0)
                    actual_home_rank = global_friend_to_home_rank.get(friend_id)
                    
                    if actual_home_rank is not None:
                        updated_friends_dict[friend_id] = {
                            "home_rank": actual_home_rank,
                            "hobbies": friend_data.get("hobbies", [])
                        }
                        
                        # Track if this friend's home rank was updated
                        if current_home_rank != actual_home_rank:
                            updated_friends += 1
                            person_updated = True
                    else:
                        # Friend ID not found in any rank, keep current values
                        updated_friends_dict[friend_id] = friend_data
                        output_logger.warning(f"Friend ID {friend_id} not found in any rank for person {person.id}")
                
            # Replace the person's friends dictionary
            person.friends = updated_friends_dict
            
            if person_updated:
                updated_people += 1
        
        # Log statistics
        # Gather statistics from all ranks
        all_updated_people = mpi_comm.allgather(updated_people)
        all_updated_friends = mpi_comm.allgather(updated_friends)
        
        if mpi_rank == 0:
            total_updated_people = sum(all_updated_people)
            total_updated_friends = sum(all_updated_friends)
            output_logger.info(f"Friends home ranks updated: {total_updated_people} people, {total_updated_friends} friend relationships")

        # Ensure all ranks are synchronized
        mpi_comm.Barrier()

    def save_checkpoint(self, saving_date):
        from june.hdf5_savers.checkpoint_saver import save_checkpoint_to_hdf5

        if mpi_size == 1:
            save_path = self.checkpoint_save_path / f"checkpoint_{saving_date}.hdf5"
        else:
            save_path = (
                self.checkpoint_save_path / f"checkpoint_{saving_date}.{mpi_rank}.hdf5"
            )
        save_checkpoint_to_hdf5(
            population=self.world.people,
            date=str(saving_date),
            hdf5_file_path=save_path,
        )