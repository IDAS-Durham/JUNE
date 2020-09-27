import logging
import datetime
import numpy as np
import pickle
import yaml
from itertools import chain
from typing import Optional, List
from pathlib import Path

from june import paths
from june.activity import ActivityManager, activity_hierarchy
from june.demography import Person, Activities
from june.exc import SimulatorError
from june.groups.leisure import Leisure
from june.groups.travel import Travel
from june.infection.symptom_tag import SymptomTag
from june.infection import InfectionSelector
from june.infection_seed import InfectionSeed
from june.interaction import Interaction, InteractiveGroup
from june.policy import Policies, MedicalCarePolicies, InteractionPolicies
from june.time import Timer
from june.world import World
from june.mpi_setup import mpi_comm, mpi_size, mpi_rank
from time import perf_counter
from time import time as wall_clock

default_config_filename = paths.configs_path / "config_example.yaml"

output_logger = logging.getLogger(__name__)


class Simulator:
    ActivityManager = ActivityManager

    def __init__(
        self,
        world: World,
        interaction: Interaction,
        timer: Timer,
        activity_manager: ActivityManager,
        infection_selector: InfectionSelector = None,
        infection_seed: Optional["InfectionSeed"] = None,
        # comment: str = None, #TODO: what do we do with comment!!
        record: Optional["Record"] = None,
        checkpoint_dates: List[datetime.date] = None,
    ):
        """
        Class to run an epidemic spread simulation on the world.

        Parameters
        ----------
        world: 
            instance of World class
        """
        self.activity_manager = activity_manager
        self.world = world
        self.interaction = interaction
        self.infection_selector = infection_selector
        self.infection_seed = infection_seed
        self.timer = timer
        #self.comment = comment
        if checkpoint_dates is None:
            self.checkpoint_dates = ()
        else:
            self.checkpoint_dates = checkpoint_dates
        self.record = record

    @classmethod
    def from_file(
        cls,
        world: World,
        interaction: Interaction,
        infection_selector=None,
        policies: Optional[Policies] = None,
        infection_seed: Optional[InfectionSeed] = None,
        leisure: Optional[Leisure] = None,
        travel: Optional[Travel] = None,
        config_filename: str = default_config_filename,
        # comment: str = None,
        record: Optional["Record"] = None,
    ) -> "Simulator":

        """
        Load config for simulator from world.yaml

        Parameters
        ----------
        leisure
        infection_seed
        policies
        interaction
        world
        config_filename
            The path to the world yaml configuration
        comment
            A brief description of the purpose of the run(s)

        Returns
        -------
        A Simulator
        """
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        if world.box_mode:
            activity_to_super_groups = None
        else:
            try:
                activity_to_super_groups = config["activity_to_super_groups"]
            except:
                output_logger.warning(
                    "Activity to groups in config is deprecated, please change it to activity_to_super_groups"
                )
                activity_to_super_groups = config["activity_to_groups"]
        time_config = config["time"]
        if "checkpoint_dates" in config:
            if isinstance(config["checkpoint_dates"], datetime.date):
                checkpoint_dates = [config["checkpoint_dates"]]
            else:
                checkpoint_dates = []
                for date_str in config["checkpoint_dates"].split():
                    checkpoint_dates.append(
                        datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                    )
        else:
            checkpoint_dates = None
        weekday_activities = [
            activity for activity in time_config["step_activities"]["weekday"].values()
        ]
        weekend_activities = [
            activity for activity in time_config["step_activities"]["weekend"].values()
        ]
        all_activities = set(
            chain.from_iterable(weekday_activities + weekend_activities)
        )

        cls.check_inputs(time_config)

        timer = Timer(
            initial_day=time_config["initial_day"],
            total_days=time_config["total_days"],
            weekday_step_duration=time_config["step_duration"]["weekday"],
            weekend_step_duration=time_config["step_duration"]["weekend"],
            weekday_activities=time_config["step_activities"]["weekday"],
            weekend_activities=time_config["step_activities"]["weekend"],
        )

        activity_manager = cls.ActivityManager(
            world=world,
            all_activities=all_activities,
            activity_to_super_groups=activity_to_super_groups,
            leisure=leisure,
            travel=travel,
            policies=policies,
            timer=timer,
        )
        return cls(
            world=world,
            interaction=interaction,
            timer=timer,
            activity_manager=activity_manager,
            infection_selector=infection_selector,
            infection_seed=infection_seed,
            # comment=comment,
            record=record,
            checkpoint_dates=checkpoint_dates,
        )

    @classmethod
    def from_checkpoint(
        cls,
        world: World,
        checkpoint_path: str,
        interaction: Interaction,
        infection_selector: Optional[InfectionSelector] = None,
        policies: Optional[Policies] = None,
        infection_seed: Optional[InfectionSeed] = None,
        leisure: Optional[Leisure] = None,
        config_filename: str = default_config_filename,
        record: Optional["Record"] = None,
    ):
        """
        Initializes the simulator from a saved checkpoint. The arguments are the same as the standard .from_file()
        initialisation but with the additional path to where the checkpoint pickle file is located.
        The checkpoint saves information about the infection status of all the people in the world as well as the timings.
        Note, nonetheless, that all the past infections / deaths will have the checkpoint date as date.
        """
        simulator = cls.from_file(
            world=world,
            interaction=interaction,
            infection_selector=infection_selector,
            policies=policies,
            infection_seed=infection_seed,
            leisure=leisure,
            config_filename=config_filename,
            record=record,
        )
        with open(checkpoint_path, "rb") as f:
            checkpoint_data = pickle.load(f)
        for dead_id in checkpoint_data["dead_ids"]:
            person = simulator.world.people.get_from_id(dead_id)
            person.dead = True
            person.susceptibility = 0.0
            cemetery = world.cemeteries.get_nearest(person)
            cemetery.add(person)
            person.subgroups = Activities(None, None, None, None, None, None, None)
        for recovered_id in checkpoint_data["recovered_ids"]:
            person = simulator.world.people.get_from_id(recovered_id)
            person.susceptibility = 0.0
        for infected_id, infection in zip(
            checkpoint_data["infected_ids"], checkpoint_data["infection_list"]
        ):
            person = simulator.world.people.get_from_id(infected_id)
            person.infection = infection
            person.susceptibility = 0.0
        # restore timer
        checkpoint_timer = checkpoint_data["timer"]
        simulator.timer.initial_date = checkpoint_timer.initial_date
        simulator.timer.date = checkpoint_timer.date
        simulator.timer.delta_time = checkpoint_timer.delta_time
        simulator.timer.shift = checkpoint_timer.shift
        return simulator

    def clear_world(self):
        """
        Removes everyone from all possible groups, and sets everyone's busy attribute
        to False.
        """
        for super_group_name in self.activity_manager.all_super_groups:
            if super_group_name in ["care_home_visits", "household_visits"]:
                continue
            grouptype = getattr(self.world, super_group_name)
            if grouptype is not None:
                for group in grouptype.members:
                    if not group.external:
                        group.clear()

        for person in self.world.people.members:
            person.busy = False
            person.subgroups.leisure = None

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

    def bury_the_dead(self, world: World, person: "Person"):
        """
        When someone dies, send them to cemetery. 
        ZOMBIE ALERT!! 

        Parameters
        ----------
        time
        person:
            person to send to cemetery
        """
        if self.record is not None:
            if person.medical_facility is not None:
                death_location = person.medical_facility.group
            else:
                death_location = person.residence.group
            self.record.accumulate(
                    table_name='deaths',
                    location_spec=death_location.spec, location_id=death_location.id, 
                    dead_person_id=person.id, 
            )
        person.dead = True
        person.infection = None
        cemetery = world.cemeteries.get_nearest(person)
        cemetery.add(person)
        if person.residence.group.spec == "household":
            household = person.residence.group
            person.residence.residents = tuple(
                mate for mate in household.residents if mate != person
            )
        person.subgroups = Activities(None, None, None, None, None, None, None)

    def recover(self, person: "Person"):
        """
        When someone recovers, erase the health information they carry and change their susceptibility.

        Parameters
        ----------
        person:
            person to recover
        time:
            time (in days), at which the person recovers
        """
        person.infection = None
        if self.record is not None:
            self.record.accumulate(table_name='recoveries',recovered_person_id=person.id)

    def update_health_status(self, time: float, duration: float):
        """
        Update symptoms and health status of infected people.
        Send them to hospital if necessary, or bury them if they
        have died.

        Parameters
        ----------
        time:
            time now
        duration:
            duration of time step
        """
        for person in self.world.people.infected:
            previous_tag = person.infection.tag
            new_status = person.infection.update_health_status(time, duration)
            if (
                previous_tag == SymptomTag.exposed
                and person.infection.tag == SymptomTag.mild
            ):
                person.residence.group.quarantine_starting_date = time
            # Take actions on new symptoms
            self.activity_manager.policies.medical_care_policies.apply(
                person=person,
                medical_facilities=self.world.hospitals,
                record=self.record,
            )
            if new_status == "recovered":
                self.recover(person)
            elif new_status == "dead":
                self.bury_the_dead(self.world, person)

    def infect_people(self, infected_ids, people_from_abroad_dict, infection_locations):
        foreign_ids, foreign_infection_locations = [], []
        for inf_id, inf_loc in zip(infected_ids, infection_locations):
            if inf_id in self.world.people.people_dict:
                person = self.world.people.get_from_id(inf_id)
                if self.record is not None:
                    self.record.accumulate(
                            table_name='infections',
                            location_spec=''.join(inf_loc.split('_')[:-1]),
                            location_id=int(inf_loc.split('_')[-1]),
                            infected_id=person.id
                    )
                self.infection_selector.infect_person_at_time(person, self.timer.now)
            else:
                foreign_ids.append(inf_id)
                foreign_infection_locations.append(inf_loc)
        if foreign_ids:
            infect_in_domains = {}
            people_ids = []
            people_domains = []
            for spec in people_from_abroad_dict:
                for group in people_from_abroad_dict[spec]:
                    for subgroup in people_from_abroad_dict[spec][group]:
                        p_ids = list(
                            people_from_abroad_dict[spec][group][subgroup].keys()
                        )
                        people_ids += p_ids
                        people_domains += [
                            people_from_abroad_dict[spec][group][subgroup][id]["dom"]
                            for id in p_ids
                        ]
            for id, domain in zip(people_ids, people_domains):
                if id in foreign_ids:
                    if domain not in infect_in_domains:
                        infect_in_domains[domain] = []
                    infect_in_domains[domain].append(
                        (id, foreign_infection_locations[foreign_ids.index(id)])
                    )
            return infect_in_domains

    def tell_domains_to_infect(self, infect_in_domains):
        people_to_infect = []
        tick, tickw = perf_counter(), wall_clock()
        for rank_sending in range(mpi_size):
            if rank_sending == mpi_rank:
                # my turn to send my data
                for rank_receiving in range(mpi_size):
                    if rank_sending == rank_receiving:
                        continue
                    if (
                        infect_in_domains is None
                        or rank_receiving not in infect_in_domains
                    ):
                        mpi_comm.send(None, dest=rank_receiving, tag=mpi_rank)
                    else:
                        mpi_comm.send(
                            infect_in_domains[rank_receiving],
                            dest=rank_receiving,
                            tag=mpi_rank,
                        )
                        continue
            else:
                # I have to listen
                data = mpi_comm.recv(source=rank_sending, tag=rank_sending)
                if data is not None:
                    people_to_infect += data
        tock, tockw = perf_counter(), wall_clock()
        output_logger.info(
            f"CMS: Infection COMS for rank {mpi_rank}/{mpi_size} - {tock-tick},{tockw-tickw} - {self.timer.date}"
        )
        for infection_data in people_to_infect:
            person = self.world.people.get_from_id(infection_data[0])
            if self.record is not None:
                self.record.accumulate(
                            table_name='infections',
                            location_spec=''.join(location_data[1].split('_')[:-1]),
                            location_id=location_data[1].split('_')[-1],
                            infected_id=person.id
                    )

            self.infection_selector.infect_person_at_time(person, self.timer.now)

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
        tick, tickw = perf_counter(), wall_clock()
        if self.activity_manager.policies is not None:
            self.activity_manager.policies.interaction_policies.apply(
                date=self.timer.date, interaction=self.interaction,
            )
        activities = self.timer.activities
        if not activities or len(activities) == 0:
            output_logger.info("==== do_timestep(): no active groups found. ====")
            return
        (
            people_from_abroad_dict,
            n_people_from_abroad,
            n_people_going_abroad,
        ) = self.activity_manager.do_timestep()

        # get the supergroup instances that are active in this time step:
        active_super_groups = self.activity_manager.active_super_groups
        super_group_instances = []
        for super_group_name in active_super_groups:
            if super_group_name not in ["household_visits", "care_home_visits"]:
                super_group_instance = getattr(self.world, super_group_name)
                if super_group_instance is None or len(super_group_instance) == 0:
                    continue
                super_group_instances.append(super_group_instance)

        # for checking that people is conserved
        n_people = 0
        # count people in the cemetery
        for cemetery in self.world.cemeteries.members:
            n_people += len(cemetery.people)
        output_logger.info(
            f"Date = {self.timer.date}, "
            f"number of deaths =  {n_people}, "
            f"number of infected = {len(self.world.people.infected)}"
        )
        # main interaction loop
        infected_ids, infection_location = [], []
        for super_group in super_group_instances:
            for group in super_group:
                if group.external:
                    continue
                if (
                    group.spec in people_from_abroad_dict
                    and group.id in people_from_abroad_dict[group.spec]
                ):
                    foreign_people = people_from_abroad_dict[group.spec][group.id]
                else:
                    foreign_people = None
                int_group = InteractiveGroup(group, foreign_people)
                n_people += int_group.size
                if int_group.must_timestep:
                    new_infected_ids = self.interaction.time_step_for_group(
                        self.timer.duration, int_group
                    )
                    if new_infected_ids:
                        n_infected = len(new_infected_ids)
                        if mpi_size == 1:
                            # note this is disabled in parallel
                            # assign blame of infections
                            tprob_norm = sum(int_group.transmission_probabilities)
                            for infector_id in chain.from_iterable(
                                int_group.infector_ids
                            ):
                                infector = self.world.people.get_from_id(infector_id)
                                assert infector.id == infector_id
                                infector.infection.number_of_infected += (
                                    n_infected
                                    * infector.infection.transmission.probability
                                    / tprob_norm
                                )
                    infected_ids += new_infected_ids
                    infection_location += len(new_infected_ids) * [
                        f"{group.spec}_{group.id}"
                    ]
        # infect the people that got exposed
        if self.infection_selector:
            infect_in_domains = self.infect_people(
                infected_ids=infected_ids,
                people_from_abroad_dict=people_from_abroad_dict,
                infection_locations=infection_location,
            )
            to_infect = self.tell_domains_to_infect(infect_in_domains)
        # recount people active to check people conservation
        people_active = (
            len(self.world.people) + n_people_from_abroad - n_people_going_abroad
        )
        if n_people != people_active:
            raise SimulatorError(
                f"Number of people active {n_people} does not match "
                f"the total people number {people_active}.\n"
                f"People in the world {len(self.world.people)}\n"
                f"People going abroad {n_people_going_abroad}\n"
                f"People coming from abroad {n_people_from_abroad}\n"
                f"Current rank {mpi_rank}\n"
            )
        # update the health status of the population
        self.update_health_status(time=self.timer.now, duration=self.timer.duration)
        if self.record is not None:
            self.record.summarise_time_step(timestamp=self.timer.date, world=self.world)
            self.record.time_step(timestamp=self.timer.date)
        # remove everyone from their active groups
        self.clear_world()
        tock, tockw = perf_counter(), wall_clock()
        output_logger.info(
            f"CMS: Timestep for rank {mpi_rank}/{mpi_size} - {tock - tick}, {tockw-tickw} - {self.timer.date}"
        )

    def run(self):
        """
        Run simulation with n_seed initial infections
        """
        output_logger.info(
            f"Starting simulation for {self.timer.total_days} days at day {self.timer.day}, to run for {self.timer.total_days} days"
        )
        self.clear_world()

        while self.timer.date < self.timer.final_date:
            if self.infection_seed:
                if (
                    self.infection_seed.max_date
                    >= self.timer.date
                    >= self.infection_seed.min_date
                ):
                    self.infection_seed.unleash_virus_per_day(
                        self.timer.date, record=self.record
                    )
            self.do_timestep()
            if (
                self.timer.date.date() in self.checkpoint_dates
                and (self.timer.now + self.timer.duration).is_integer()
            ):  # this saves in the last time step of the day
                saving_date = self.timer.date.date()
                next(self.timer)  # we want to save at the next time step so that
                # we can resume consistenly
                output_logger.info(
                    f"Saving simulation checkpoint at {self.timer.date.date()}"
                )
                self.save_checkpoint(saving_date)
                continue
            next(self.timer)

    def save_checkpoint(self, date: datetime):
        """
        Saves a checkpoint at the given date. We save all the health information of the
        population. We can then load the world back to the checkpoint state using the
        from_checkpoint class method of this class.
        """
        recovered_people_ids = [
            person.id for person in self.world.people if person.recovered
        ]
        dead_people_ids = [person.id for person in self.world.people if person.dead]
        susceptible_people_ids = [
            person.id for person in self.world.people if person.susceptible
        ]
        infected_people_ids = []
        infection_list = []
        for person in self.world.people.infected:
            infected_people_ids.append(person.id)
            infection_list.append(person.infection)
        checkpoint_data = {
            "recovered_ids": recovered_people_ids,
            "dead_ids": dead_people_ids,
            "susceptible_ids": susceptible_people_ids,
            "infected_ids": infected_people_ids,
            "infection_list": infection_list,
            "timer": self.timer,
        }
        with open(self.record.record_path / f"checkpoint_{str(date)}.pkl", "wb") as f:
            pickle.dump(checkpoint_data, f)
