import logging
import yaml
from datetime import datetime
from itertools import chain
from typing import List, Optional
from time import perf_counter
from time import time as wall_clock

from june.demography import Person
from june.exc import SimulatorError
from june.global_context import GlobalContext
from june.groups import Subgroup
from june.groups.leisure import Leisure
from june.groups.travel import Travel
from june.mpi_wrapper import MPI, mpi_comm, mpi_size, mpi_rank, MovablePeople
from june.records import Record

logger = logging.getLogger("activity_manager")
mpi_logger = logging.getLogger("mpi")
rank_logger = logging.getLogger("rank")
if mpi_rank > 0:
    logger.propagate = True

activity_hierarchy = [
    "medical_facility", # Keep medical as highest priority
    "international_travel",           # Add international travel with high priority
    "rail_travel_out",
    "rail_travel_back",
    "commute",
    "primary_activity",
    "leisure",
    "residence",
]


class ActivityManager:
    def __init__(
        self,
        world,
        policies,
        timer,
        all_activities,
        activity_to_super_groups: dict,
        record: Optional[Record] = None,
        leisure: Optional[Leisure] = None,
        travel: Optional[Travel] = None,
    ):
        self.policies = policies
        if self.policies is not None:
            self.policies.init_policies(world=world, date=timer.date, record=record)
        self.world = world
        self.timer = timer
        self.leisure = leisure
        self.travel = travel
        self.all_activities = all_activities

        self.activity_to_super_group_dict = {
            "medical_facility": activity_to_super_groups.get("medical_facility", []),
            "international_travel": activity_to_super_groups.get("international_travel", []),
            "primary_activity": activity_to_super_groups.get("primary_activity", []),
            "leisure": activity_to_super_groups.get("leisure", []),
            "residence": activity_to_super_groups.get("residence", []),
            "commute": activity_to_super_groups.get("commute", []),
            "rail_travel": activity_to_super_groups.get("rail_travel", []),
        }

    @classmethod
    def from_file(
        cls,
        config_filename,
        world,
        policies,
        timer,
        record: Optional[Record] = None,
        leisure: Optional[Leisure] = None,
        travel: Optional[Travel] = None,
    ):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        try:
            activity_to_super_groups = config["activity_to_super_groups"]
        except KeyError:
            logger.warning(
                "Activity to groups in config is deprecated"
                "please change it to activity_to_super_groups"
            )
            activity_to_super_groups = config["activity_to_groups"]
        time_config = config["time"]

        cls.check_inputs(time_config)
        weekday_activities = [
            activity for activity in time_config["step_activities"]["weekday"].values()
        ]
        weekend_activities = [
            activity for activity in time_config["step_activities"]["weekend"].values()
        ]
        all_activities = set(
            chain.from_iterable(weekday_activities + weekend_activities)
        )
        return cls(
            world=world,
            policies=policies,
            timer=timer,
            all_activities=all_activities,
            activity_to_super_groups=activity_to_super_groups,
            leisure=leisure,
            travel=travel,
            record=record,
        )

    @staticmethod
    def check_inputs(time_config: dict):
        """
        Check that the iput time configuration is correct, i.e., activities are among allowed activities
        and days have 24 hours.

        Parameters
        ----------
        time_config:
            dictionary with time steps configuration
        """

        try:
            assert sum(time_config["step_duration"]["weekday"].values()) == 24
            assert sum(time_config["step_duration"]["weekend"].values()) == 24
        except AssertionError:
            raise SimulatorError(
                "Daily activity durations in config do not add to 24 hours."
            )

        # Check that all groups given in time_config file are in the valid group hierarchy
        all_super_groups = activity_hierarchy
        try:
            for step, activities in time_config["step_activities"]["weekday"].items():
                assert all(group in all_super_groups for group in activities)

            for step, activities in time_config["step_activities"]["weekend"].items():
                assert all(group in all_super_groups for group in activities)
        except AssertionError:
            raise SimulatorError("Config file contains unsupported activity name.")

    @property
    def all_super_groups(self):
        return self.activities_to_super_groups(self.all_activities)

    @property
    def active_super_groups(self):
        return self.activities_to_super_groups(self.timer.activities)

    @staticmethod
    def apply_activity_hierarchy(activities: List[str]) -> List[str]:
        """
        Returns a list of activities with the right order, obeying the permanent activity hierarchy
        and shuffling the random one.

        Parameters
        ----------
        activities:
            list of activities that take place at a given time step
        Returns
        -------
        Ordered list of activities according to hierarchy
        """
        print(f"Original Activities: {activities}")

        # Sort activities according to the activity hierarchy
        activities.sort(key=lambda x: activity_hierarchy.index(x))
        
        print(f"Ordered Activities: {activities}")
        return activities

    def activities_to_super_groups(self, activities: List[str]) -> List[str]:
        """
        Converts activities into Supergroups, the interaction will run over these Groups.

        Parameters
        ---------
        activities:
            list of activities that take place at a given time step
        Returns
        -------
        List of groups that are active.
        """
        return list(
            chain.from_iterable(
                self.activity_to_super_group_dict[activity] for activity in activities
            )
        )

    def get_personal_subgroup(self, person: "Person", activity: str):
        return getattr(person, activity)

    def do_timestep(self, record=None):
        # get time data
        tick_interaction_timestep = perf_counter()
        date = self.timer.date
        day_type = self.timer.day_type
        activities = self.apply_activity_hierarchy(self.timer.activities)
        delta_time = self.timer.duration
        # apply leisure policies
        if self.leisure is not None:
            if self.policies is not None:
                self.policies.leisure_policies.apply(date=date, leisure=self.leisure)
            self.leisure.generate_leisure_probabilities_for_timestep(
                delta_time=delta_time,
                date=date,
                working_hours="primary_activity" in activities,
            )
        
        # move people to subgroups and get going abroad people
        to_send_abroad, potential_leisure_inviters = self.move_people_to_active_subgroups(
            activities=activities,
            date=date,
            days_from_start=self.timer.now,
            record=record,
        )
        
        # process friend invitations for leisure activities
        # IMPORTANT: All ranks must participate in friend invitation process for MPI synchronization
        simulator = GlobalContext.get_simulator()
        if simulator.friend_hangouts_enabled:
            if self.leisure is not None and "leisure" in activities:
                logger.info("Starting friend invitation process...")
                # ALL ranks must participate in the friend invitation process for MPI synchronization
                self.leisure.process_friend_invitations(potential_leisure_inviters, self.world)
                
                # collect additional transfers from friend acceptances
                additional_transfers = self.collect_friend_transfers()
                # manually merge additional transfers into to_send_abroad
                self._merge_movable_people(to_send_abroad, additional_transfers)
                logger.info("Friend invitation process finished.")

        tock_interaction_timestep = perf_counter()
        rank_logger.info(
            f"Rank {mpi_rank} -- move_people -- {tock_interaction_timestep-tick_interaction_timestep}"
        )
        tick_waiting = perf_counter()
        mpi_comm.Barrier()
        tock_waiting = perf_counter()
        rank_logger.info(
            f"Rank {mpi_rank} -- move_people_waiting -- {tock_waiting-tick_waiting}"
        )
        (
            people_from_abroad,
            n_people_from_abroad,
            n_people_going_abroad,
        ) = self.send_and_receive_people_from_abroad(to_send_abroad)
        return (
            people_from_abroad,
            n_people_from_abroad,
            n_people_going_abroad,
            to_send_abroad,
        )

    def move_people_to_active_subgroups(
        self,
        activities: List[str],
        date: datetime = datetime(2020, 2, 2),
        days_from_start=0,
        record=None,
    ):
        """
        Sends every person to one subgroup. If a person has a mild illness,
        they stay at home

        Parameters
        ----------

        """
        tick = perf_counter()
        active_individual_policies = self.policies.individual_policies.get_active(
            date=date
        )
        to_send_abroad = MovablePeople()
        potential_leisure_inviters = []  # Track people who got assigned to leisure
        counter = 0
        for person in self.world.people:
            counter += 1
            if person.dead or person.busy:
                continue
            allowed_activities = self.policies.individual_policies.apply(
                active_policies=active_individual_policies,
                person=person,
                activities=activities,
                days_from_start=days_from_start,
            )
            external_subgroup = self.move_to_active_subgroup(
                allowed_activities, person, to_send_abroad, potential_leisure_inviters
            )
            if external_subgroup is not None:
                to_send_abroad.add_person(person, external_subgroup)

        tock = perf_counter()
        mpi_logger.info(f"{self.timer.date},{mpi_rank},activity,{tock-tick}")
        return to_send_abroad, potential_leisure_inviters
    
    def collect_friend_transfers(self):
        """
        Collect people who accepted friend invitations and need to be transferred to other ranks.
        
        Returns
        -------
        MovablePeople
            Container with people who need to be transferred
        """        
        additional_transfers = MovablePeople()
        transfer_count = 0
        
        for person in self.world.people:
            if (person.subgroups.leisure and 
                person.subgroups.leisure.external and 
                not person.busy):  # Not already flagged in normal assignment
                
                person.busy = True
                additional_transfers.add_person(person, person.subgroups.leisure)
                transfer_count += 1
                
        return additional_transfers
    
    def _merge_movable_people(self, primary, additional):
        """
        Merge additional MovablePeople into the primary MovablePeople object.
        
        Parameters
        ----------
        primary : MovablePeople
            The main container to merge into
        additional : MovablePeople
            The additional container to merge from
        """        
        merged_domains = 0
        merged_people = 0
        
        # Merge skinny_out dictionaries
        for domain_id, domain_data in additional.skinny_out.items():
            
            if domain_id not in primary.skinny_out:
                primary.skinny_out[domain_id] = {}
            
            for group_spec, spec_data in domain_data.items():
                if group_spec not in primary.skinny_out[domain_id]:
                    primary.skinny_out[domain_id][group_spec] = {}
                
                for group_id, group_data in spec_data.items():
                    if group_id not in primary.skinny_out[domain_id][group_spec]:
                        primary.skinny_out[domain_id][group_spec][group_id] = {}
                    
                    for subgroup_type, subgroup_data in group_data.items():
                        if subgroup_type not in primary.skinny_out[domain_id][group_spec][group_id]:
                            primary.skinny_out[domain_id][group_spec][group_id][subgroup_type] = {}
                        
                        # Merge person data
                        before_count = len(primary.skinny_out[domain_id][group_spec][group_id][subgroup_type])
                        primary.skinny_out[domain_id][group_spec][group_id][subgroup_type].update(subgroup_data)
                        after_count = len(primary.skinny_out[domain_id][group_spec][group_id][subgroup_type])
                        people_added = after_count - before_count
                        merged_people += people_added
            
            merged_domains += 1
        
    def move_to_active_subgroup(
        self, activities: List[str], person: Person, to_send_abroad=None, potential_leisure_inviters=None
    ) -> Optional["Subgroup"]:
        """
        Given the hierarchy of activities and a person, decide what subgroup
        should they go to

        Parameters
        ----------
        activities:
            list of activities that take place at a given time step
        person:
            person that is looking for a subgroup to go to
        potential_leisure_inviters:
            list to track people who get assigned to leisure activities
        Returns
        -------
        Subgroup to which person has to go, given the hierarchy of activities
        """
        for activity in activities:
            if activity == "leisure" and person.leisure is None:
                subgroup = self.leisure.get_subgroup_for_person_and_housemates(
                    person=person, to_send_abroad=to_send_abroad
                )
                # Track this person as a potential inviter if they got leisure
                if subgroup is not None and potential_leisure_inviters is not None:
                    potential_leisure_inviters.append(person)
            elif activity == "commute":
                subgroup = self.travel.get_commute_subgroup(person=person)
            else:
                subgroup = self.get_personal_subgroup(person=person, activity=activity)
            if subgroup is not None:
                if subgroup.external:
                    person.busy = True
                    # this person goes to another MPI domain
                    return subgroup

                subgroup.append(person)
                return
        raise SimulatorError(
            "Attention! Some people do not have an activity in this timestep."
        )

    def send_and_receive_people_from_abroad(self, movable_people):
        """
        Deal with the MPI comms.
        """
        n_people_going_abroad = 0
        n_people_from_abroad = 0
        tick, tickw = perf_counter(), wall_clock()
        reqs = []

        for rank in range(mpi_size):

            if mpi_rank == rank:
                continue
            keys, data, n_this_rank = movable_people.serialise(rank)
            if n_this_rank:
                reqs.append(mpi_comm.isend(keys, dest=rank, tag=100))
                reqs.append(mpi_comm.isend(data, dest=rank, tag=200))
                n_people_going_abroad += n_this_rank
            else:
                reqs.append(mpi_comm.isend(None, dest=rank, tag=100))
                reqs.append(mpi_comm.isend(None, dest=rank, tag=200))

        # now it has all been sent, we can start the receiving.

        for rank in range(mpi_size):

            if rank == mpi_rank:
                continue
            keys = mpi_comm.recv(source=rank, tag=100)
            data = mpi_comm.recv(source=rank, tag=200)

            if keys is not None:
                movable_people.update(rank, keys, data)
                n_people_from_abroad += data.shape[0]

        for r in reqs:
            r.wait()

        tock, tockw = perf_counter(), wall_clock()
        logger.info(
            f"CMS: People COMS for rank {mpi_rank}/{mpi_size} - {tock - tick},{tockw - tickw} - {self.timer.date}"
        )
        mpi_logger.info(f"{self.timer.date},{mpi_rank},people_comms,{tock-tick}")
        return movable_people.skinny_in, n_people_from_abroad, n_people_going_abroad
