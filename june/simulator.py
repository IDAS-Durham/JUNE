import logging
import random
from june import paths
from typing import List

from itertools import chain
import numpy as np
import yaml

from june.demography import Person
from june.groups import Group
from june.infection import Infection
from june.infection.health_index import HealthIndexGenerator
from june.interaction import Interaction
from june.logger_simulation import Logger
from june.time import Timer
from june.world import World

default_config_filename = paths.configs_path / "config_example.yaml"

sim_logger = logging.getLogger(__name__)


class SimulatorError(BaseException):
    pass


# TODO: Split the config into more manageable parts for tests
class Simulator:
    def __init__(
        self,
        world: World,
        interaction: Interaction,
        infection: Infection,
        config: dict,
    ):
        """
        Class to run an epidemic spread simulation on the world

        Parameters
        ----------
        world: 
            instance of World class
        interaction:
            instance of Interaction class, determines
             
        config:
            dictionary with configuration to set up the simulation
        """
        self.world = world
        self.interaction = interaction
        self.infection = infection
        self.permanent_activity_hierarchy = [
            "boxes",
            "hospital",
            "commute",
            "primary_activity",
            "residence",
        ]
        self.randomly_order_activities = [
            "pubs",
            "churches",
        ]
        self.check_inputs(config["time"])
        self.health_index_generator = HealthIndexGenerator.from_file()
        self.timer = Timer(config["time"])
        self.logger = Logger(
            self, self.world, self.timer, config["logger"]["save_path"],
        )
        self.all_activities = set(
            chain(
                *(
                    [
                        activity
                        for activity in config["time"]["step_activities"][
                            "weekday"
                        ].values()
                    ]
                    + [
                        activity
                        for activity in config["time"]["step_activities"][
                            "weekend"
                        ].values()
                    ]
                )
            )
        )

        self.activity_to_group_dict = {
            "hospital": ["hospitals"],
            "primary_activity": ["schools", "companies"],
            "residence": ["households", "carehomes"],
        }

    @classmethod
    def from_file(
        cls,
        world: "World",
        interaction: "Interaction",
        infection: Infection,
        config_filename: str = default_config_filename,
    ) -> "Simulator":

        """
        Load config for simulator from world.yaml

        Parameters
        ----------
        config_filename
            The path to the world yaml configuration

        Returns
        -------
        A Simulator
        """
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return Simulator(world, interaction, infection, config)

    def check_inputs(self, config: dict):
        """
        Check that the iput time configuration is correct, i.e., activities are among allowed activities
        and days have 24 hours.

        Parameters
        ----------
        config
            dictionary with time steps configuration
        """

        # Sadly, days only have 24 hours
        assert sum(config["step_duration"]["weekday"].values()) == 24
        # even during the weekend :(
        assert sum(config["step_duration"]["weekend"].values()) == 24

        # Check that all groups given in config file are in the valid group hierarchy
        all_groups = self.permanent_activity_hierarchy + self.randomly_order_activities
        for step, activities in config["step_activities"]["weekday"].items():
            assert all(group in all_groups for group in activities)

        for step, activities in config["step_activities"]["weekend"].items():
            assert all(group in all_groups for group in activities)

    def apply_activity_hierarchy(self, activities: List[str]) -> List[str]:
        """
        Returns a list of activities with the right order, obeying the permanent activity hierarcy
        and shuflling the random one. It is very important having carehomes and households at the very end.

        Parameters
        ----------
        active_groups:
            list of groups that are active at a given time step
        Returns
        -------
        Ordered list of active groups according to hierarchy
        """
        random.shuffle(self.randomly_order_activities)
        activity_hierarchy = [
            group for group in self.permanent_activity_hierarchy if group != "residence"
        ]
        activity_hierarchy += self.randomly_order_activities + ["residence"]
        activities.sort(key=lambda x: activity_hierarchy.index(x))
        return activities

    def activities_to_groups(self, activities):
        groups = [self.activity_to_group_dict[activity] for activity in activities]
        return list(chain(*groups))

    def clear_all_groups(self):
        for group_name in self.activities_to_groups(self.all_activities):
            grouptype = getattr(self.world, group_name)
            for group in grouptype.members:
                for subgroup in group.subgroups:
                    subgroup._people.clear()

    def get_subgroup_active(self, activities, person: "Person"):

        activities = self.apply_activity_hierarchy(activities)
        for group_name in activities:
            subgroup = getattr(person, group_name)
            if subgroup is not None:
                return subgroup

    def move_people_to_active_subgroups(self, activities: List[str]):
        """
        Sends every person to one subgroup.

        Parameters
        ----------
        active_groups:
            list of groups that are active at a time step
        """
        for person in self.world.people.members:
            if not person.health_information.dead:
                subgroup = self.get_subgroup_active(activities, person)
                subgroup.append(person)

    def hospitalise_the_sick(self, person, previous_tag):
        """
        These functions could be more elegantly handled by an implementation inside a group collection.
        I'm putting them here for now to maintain the same functionality whilst removing a person's
        reference to the world as that makes it impossible to perform population generation prior
        to world construction.

        Parameters
        ---------
        person:
            person to hospitalise
        """
        if person.hospital is None:
            self.world.hospitals.allocate_patient(person)
        elif previous_tag != person.health_information.tag:
            person.hospital.group.move_patient_within_hospital(person)

    def bury_the_dead(self, person: "Person", time: float):
        """
        When someone dies, send them to cemetery. 
        ZOMBIE ALERT!! Specially important, remove from all groups in which
        that person was present. 

        Parameters
        ---------
        person:
            person sent to cemetery
        """
        cemetery = self.world.cemeteries.get_nearest(person)
        cemetery.add(person)
        person.health_information.set_dead(time)

    def update_health_status(self, time: float, delta_time: float):
        """
        Update symptoms and health status of infected people

        Parameters
        ----------
        time:
            time now
        delta_time:
            duration of time step
        """

        for person in self.world.people.infected:
            health_information = person.health_information
            previous_tag = health_information.tag
            health_information.update_health_status(time, delta_time)
            # release patients that recovered
            if health_information.recovered:
                if person.hospital is not None:
                    person.hospital.group.release_as_patient(person)
                health_information.set_recovered(time)
            elif health_information.should_be_in_hospital:
                self.hospitalise_the_sick(person, previous_tag)
            elif health_information.is_dead and not self.world.box_mode:
                self.bury_the_dead(person, time)

    def do_timestep(self):
        """
        Perform a time step in the simulation

        """
        activities = self.timer.activities()
        if not activities or len(activities) == 0:
            sim_logger.info("==== do_timestep(): no active groups found. ====")
            return
        self.move_people_to_active_subgroups(activities)
        active_groups = self.activities_to_groups(activities)
        group_instances = [getattr(self.world, group) for group in active_groups]
        n_people = 0
        if not self.world.box_mode:
            for cemetery in self.world.cemeteries.members:
                n_people += len(cemetery.people)
        sim_logger.info(f"number of deaths =  {n_people}")
        for group_type in group_instances:
            n_active_in_group = 0
            for group in group_type.members:
                self.interaction.time_step(
                    self.timer.now,
                    self.health_index_generator,
                    self.timer.duration,
                    group,
                )
                n_active_in_group += group.size
                n_people += group.size
            sim_logger.info(f"Active in {group.spec} = {n_active_in_group}")

        # assert conservation of people
        if n_people != len(self.world.people.members):
            raise SimulatorError(
                f"Number of people active {n_people} does not match "
                f"the total people number {len(self.world.people.members)}"
            )

        self.update_health_status(self.timer.now, self.timer.duration)
        self.clear_all_groups()

    def run(self, save=False):
        """
        Run simulation with n_seed initial infections

        Parameters
        ----------
        save:
            whether to save the last state of the world

        """
        sim_logger.info(
            f"Starting group_dynamics for {self.timer.total_days} days at day {self.timer.day}"
        )
        sim_logger.info(
            f"starting the loop ..., at {self.timer.day} days, to run for {self.timer.total_days} days"
        )
        self.clear_all_groups()
        for day in self.timer:
            if day > self.timer.total_days:
                break
            self.logger.log_timestep(day)
            self.do_timestep()
        # Save the world
        if save:
            self.world.to_pickle("world.pickle")
