import logging
from itertools import chain
from typing import Optional

import yaml

from june import paths
from june.activity import ActivityManager, activity_hierarchy
from june.demography import Person, Activities
from june.exc import SimulatorError
from june.groups.leisure import Leisure
from june.infection.symptom_tag import SymptomTag
from june.infection_seed import InfectionSeed
from june.interaction import ContactAveraging
from june.logger.logger import Logger
from june.policy import Policies
from june.time import Timer
from june.world import World

default_config_filename = paths.configs_path / "config_example.yaml"

logger = logging.getLogger(__name__)


class Simulator:
    ActivityManager = ActivityManager

    def __init__(
            self,
            world: World,
            interaction,
            timer: Timer,
            activity_manager: ActivityManager,
            infection_seed: Optional["InfectionSeed"] = None,
            save_path: str = "results",
            output_filename: str = "logger.hdf5",
            light_logger: bool = False,
    ):
        """
        Class to run an epidemic spread simulation on the world

        Parameters
        ----------
        world: 
            instance of World class
        save_path:
            path to save logger results
        """
        self.activity_manager = activity_manager
        self.world = world
        self.interaction = interaction
        self.infection_seed = infection_seed
        self.light_logger = light_logger
        self.timer = timer
        if not self.world.box_mode:
            self.logger = Logger(save_path=save_path, file_name=output_filename)
        else:
            self.logger = None

    @classmethod
    def from_file(
            cls,
            world: "World",
            interaction: "ContactAveraging",
            policies: Optional["Policies"] = None,
            infection_seed: Optional["InfectionSeed"] = None,
            leisure: Optional["Leisure"] = None,
            config_filename: str = default_config_filename,
            save_path: str = "results",
    ) -> "Simulator":

        """
        Load config for simulator from world.yaml

        Parameters
        ----------
        save_path
        leisure
        infection_seed
        policies
        interaction
        world
        config_filename
            The path to the world yaml configuration

        Returns
        -------
        A Simulator
        """
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        if world.box_mode:
            activity_to_groups = None
        else:
            activity_to_groups = config["activity_to_groups"]
        time_config = config["time"]
        weekday_activities = [
            activity for activity in time_config["step_activities"]["weekday"].values()
        ]
        weekend_activities = [
            activity for activity in time_config["step_activities"]["weekend"].values()
        ]
        all_activities = set(chain(*(weekday_activities + weekend_activities)))

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
            activity_to_groups=activity_to_groups,
            leisure=leisure,
            policies=policies,
            timer=timer,
            interaction=interaction,
        )
        return cls(
            world=world,
            activity_manager=activity_manager,
            timer=timer,
            infection_seed=infection_seed,
            save_path=save_path,
            interaction=interaction
        )

    def clear_world(self):
        """
        Removes everyone from all possible groups, and sets everyone's busy attribute
        to False.

        """
        for group_name in self.activity_manager.all_groups:
            if group_name in ["care_home_visits", "household_visits"]:
                continue
            grouptype = getattr(self.world, group_name)
            if grouptype is not None:
                for group in grouptype.members:
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

        # Sadly, days only have 24 hours
        assert sum(time_config["step_duration"]["weekday"].values()) == 24
        # even during the weekend :(
        assert sum(time_config["step_duration"]["weekend"].values()) == 24

        # Check that all groups given in time_config file are in the valid group hierarchy
        all_groups = activity_hierarchy
        for step, activities in time_config["step_activities"]["weekday"].items():
            assert all(group in all_groups for group in activities)

        for step, activities in time_config["step_activities"]["weekend"].items():
            assert all(group in all_groups for group in activities)

    def hospitalise_the_sick(self, person: "Person", previous_tag: str):
        """
        Hospitalise sick person. Also moves them from a regular bed
        to an ICU bed if their symptoms tag has changed.

        Parameters
        ----------
        person:
            person to hospitalise
        previous_tag:
            previous symptoms tag of a person
        """
        if person.hospital is None:
            self.world.hospitals.allocate_patient(person)
        elif previous_tag != person.health_information.tag:
            person.hospital.group.move_patient_within_hospital(person)

    def bury_the_dead(self, person: "Person", time: float):
        """
        When someone dies, send them to cemetery. 
        ZOMBIE ALERT!! 

        Parameters
        ----------
        time
        person:
            person to send to cemetery
        """
        person.dead = True
        cemetery = self.world.cemeteries.get_nearest(person)
        cemetery.add(person)
        person.health_information.set_dead(time)
        person.subgroups = Activities(None, None, None, None, None, None, None)

    @staticmethod
    def recover(person: "Person", time: float):
        """
        When someone recovers, erase the health information they carry and change their susceptibility.

        Parameters
        ----------
        person:
            person to recover
        time:
            time (in days), at which the person recovers
        """
        # TODO: seems to be only used to set the infection length at the moment, but this is not logged
        # anywhere, so we could get rid of this potentially
        person.health_information.set_recovered(time)
        person.susceptibility = 0.0
        person.health_information = None

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
        ids = []
        symptoms = []
        n_secondary_infections = []
        for person in self.world.people.infected:
            health_information = person.health_information
            previous_tag = health_information.tag
            health_information.update_health_status(time, duration)
            if (
                previous_tag == SymptomTag.exposed
                and health_information.tag == SymptomTag.mild
            ):
                person.residence.group.quarantine_starting_date = time
            ids.append(person.id)
            symptoms.append(person.health_information.tag.value)
            n_secondary_infections.append(person.health_information.number_of_infected)
            # Take actions on new symptoms
            if health_information.recovered:
                if person.hospital is not None:
                    person.hospital.group.release_as_patient(person)
                self.recover(person, time)
            elif health_information.should_be_in_hospital:
                self.hospitalise_the_sick(person, previous_tag)
            elif health_information.is_dead:
                self.bury_the_dead(person, time)
        if self.logger:
            self.logger.log_infected(
                self.timer.date, ids, symptoms, n_secondary_infections
            )

    def do_timestep(self):
        """
        Perform a time step in the simulation

        """
        activities = self.timer.activities
        if not activities or len(activities) == 0:
            logger.info("==== do_timestep(): no active groups found. ====")
            return

        self.activity_manager.do_timestep()

        active_groups = self.activity_manager.active_groups
        group_instances = [
            getattr(self.world, group)
            for group in active_groups
            if group not in ["household_visits", "care_home_visits"]
        ]
        n_people = 0

        for cemetery in self.world.cemeteries.members:
            n_people += len(cemetery.people)
        logger.info(
            f"Date = {self.timer.date}, "
            f"number of deaths =  {n_people}, "
            f"number of infected = {len(self.world.people.infected)}"
        )
        for group_type in group_instances:
            n_people_group = 0
            for group in group_type.members:
                self.interaction.time_step(
                    self.timer.now, self.timer.duration, group, self.logger,
                )
                n_people += group.size
                n_people_group += group.size

        if n_people != len(self.world.people.members):
            raise SimulatorError(
                f"Number of people active {n_people} does not match "
                f"the total people number {len(self.world.people.members)}"
            )

        self.update_health_status(time=self.timer.now, duration=self.timer.duration)
        if self.logger:
            self.logger.log_infection_location(self.timer.date)
            self.logger.log_hospital_capacity(self.timer.date, self.world.hospitals)
        self.clear_world()

    def run(self):
        """
        Run simulation with n_seed initial infections
        """
        logger.info(
            f"Starting group_dynamics for {self.timer.total_days} days at day {self.timer.day}"
        )
        logger.info(
            f"starting the loop ..., at {self.timer.day} days, to run for {self.timer.total_days} days"
        )
        self.clear_world()
        if self.logger:
            self.logger.log_population(
                self.world.people, light_logger=self.light_logger
            )
            self.logger.log_hospital_characteristics(self.world.hospitals)
            self.logger.log_parameters(
                self.interaction,self.infection_seed,self.policies,self.leisure
            )
        for time in self.timer:
            if time > self.timer.final_date:
                break
            if self.infection_seed:
                if self.infection_seed.max_date >= time >= self.infection_seed.min_date:
                    self.infection_seed.unleash_virus_per_region(time)
            self.do_timestep()
