import logging
import random
from june import paths
from typing import List

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
        self.permanent_group_hierarchy = [
            "boxes",
            "hospitals",
            "commute",
            "companies",
            "schools",
            "carehomes",
            "households",
        ]
        self.randomly_order_groups = [
            "pubs",
            "churches",
        ]
        self.check_inputs(config["time"])
        self.health_index_generator = HealthIndexGenerator.from_file()
        self.timer = Timer(config["time"])
        self.logger = Logger(
            self, self.world, self.timer, config["logger"]["save_path"],
        )

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

        # Sadly, days only have 24 hours
        assert sum(config["step_duration"]["weekday"].values()) == 24
        # even during the weekend :(
        assert sum(config["step_duration"]["weekend"].values()) == 24

        # Check that all groups given in config file are in the valid group hierarchy
        all_groups = self.permanent_group_hierarchy + self.randomly_order_groups
        for step, active_groups in config["step_active_groups"]["weekday"].items():
            assert all(group in all_groups for group in active_groups)

        for step, active_groups in config["step_active_groups"]["weekend"].items():
            assert all(group in all_groups for group in active_groups)

    def apply_group_hierarchy(self, active_groups: List[str]) -> List[str]:
        """
        Returns a list of active groups with the right order, obeying the permanent group hierarcy
        and shuflling the random one. It is very important having carehomes and households at the very end.

        Parameters
        ----------
        active_groups:
            list of groups that are active at a given time step
        Returns
        -------
        Ordered list of active groups according to hierarchy
        """
        random.shuffle(self.randomly_order_groups)
        group_hierarchy = [
            group
            for group in self.permanent_group_hierarchy
            if group not in ["carehomes", "households"]
        ]
        group_hierarchy += self.randomly_order_groups + ["carehomes", "households"]
        active_groups.sort(key=lambda x: group_hierarchy.index(x))
        return active_groups

    def set_active_group_to_people(self, active_groups: List[str]):
        """
        Calls the set_active_members() method of each group, if the group
        is set as active

        Parameters
        ----------
        active_groups:
            list of groups that are active at a time step
        """
        active_groups = self.apply_group_hierarchy(active_groups)
        # patients in hospitals are always active
        for hospital in self.world.hospitals.members:
            hospital.set_active_patients()
            
        for group_name in active_groups:
            grouptype = getattr(self.world, group_name)
            if "pubs" in active_groups:
                self.world.group_maker.distribute_people(group_name)
            if "commute" in active_groups:
                self.world.group_maker.distribute_people(group_name)
            for group in grouptype.members:
                if group.spec == 'household':
                    group.set_active_members()
                else:
                    for subgroup in group.subgroups:
                        subgroup.set_active_members()

    def set_allpeople_free(self):
        """ 
        Set everyone's active group to None, 
        ready for next time step
        """
        for person in self.world.people.members:
            person.active_group = None

    def hospitalise_the_sick(self, person):
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
        if person.in_hospital is None:
            self.world.hospitals.allocate_patient(person)

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
        for subgroup in person.subgroups:
            if subgroup is not None:
                subgroup.remove(person)
        person.active_group = None
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
            health_information.update_health_status(time, delta_time)
            # release patients that recovered
            if health_information.recovered:
                if person.in_hospital is not None:
                    person.in_hospital.release_as_patient(person)
                health_information.set_recovered(time)

            elif health_information.in_hospital:
                self.hospitalise_the_sick(person)

            elif health_information.is_dead and not self.world.box_mode:
                self.bury_the_dead(person, time)

    def do_timestep(self):
        """
        Perform a time step in the simulation

        """
        sim_logger.info("******* TIME STEP *******")
        active_groups = self.timer.active_groups()
        if not active_groups or len(active_groups) == 0:
            sim_logger.info("==== do_timestep(): no active groups found. ====")
            return
        # update people (where they are according to time)
        self.set_active_group_to_people(active_groups)
        # infect people in groups
        group_instances = [getattr(self.world, group) for group in active_groups]
        n_people = 0
        if not self.world.box_mode:
            for cemetery in self.world.cemeteries.members:
                n_people += len(cemetery.people)
        sim_logger.info(f'number of deaths =  {n_people}')
        for group_type in group_instances:
            n_active_in_group = 0
            for group in group_type.members:
                self.interaction.time_step(
                    self.timer.now,
                    self.health_index_generator,
                    self.timer.duration,
                    group,
                )
                n_active_in_group += group.size_active
                n_people += group.size_active 
            sim_logger.info(f"Active in {group.spec} = {n_active_in_group}")

        for person in self.world.people.members:
            if not person.health_information.dead and person.active_group is None:
                print([subgroup.spec for subgroup in person.subgroups if subgroup is not None])
                print(person.health_information.tag)
                assert person in person.subgroups[person.GroupType.residence].people 

       # assert conservation of people
        if n_people != len(self.world.people.members):
            raise SimulatorError(
                f"Number of people active {n_people} does not match "
                f"the total people number {len(self.world.people.members)}"
            )

        self.update_health_status(self.timer.now, self.timer.duration)
        self.set_allpeople_free()

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

        for day in self.timer:
            if day > self.timer.total_days:
                break
            self.logger.log_timestep(day)
            self.do_timestep()
        # Save the world
        if save:
            self.world.to_pickle(
                "world.pickle"
            )
