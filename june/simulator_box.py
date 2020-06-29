import copy
import logging
import random
from datetime import datetime
from itertools import chain
from typing import List, Optional

import yaml

from june import paths
from june.demography import Person, Activities
from june.groups.commute.commutecityunit_distributor import CommuteCityUnitDistributor
from june.groups.commute.commuteunit_distributor import CommuteUnitDistributor
from june.groups.travel.travelunit_distributor import TravelUnitDistributor
from june.infection.infection import InfectionSelector
from june.interaction import Interaction
from june.logger.logger import Logger
from june.policy import Policies
from june.time import Timer
from june.world import World, possible_groups
from june.simulator import Simulator
from june.infection.symptom_tag import SymptomTag

default_config_filename = paths.configs_path / "config_example.yaml"

sim_logger = logging.getLogger(__name__)


class SimulatorError(BaseException):
    pass


class SimulatorBox(Simulator):
    def __init__(
        self,
        world: World,
        interaction: Interaction,
        selector: InfectionSelector,
        activity_to_groups: dict,
        time_config: dict,
        infection_seed: Optional["InfectionSeed"] = None,
        leisure: Optional["Leisure"] = None,
        min_age_home_alone: int = 15,
        stay_at_home_complacency: float = 0.95,
        policies=Policies(),
        save_path: str = "results",
        output_filename: str = "logger.hdf5",
        light_logger: bool = False,
    ):
        """
        Class to run an epidemic spread simulation on a box. It is 
        basically a wrapper around the Simualtor class, disabling
        the options that are not available in box mode, like
        moving ill people to households.

        Parameters
        ----------
        world: 
            instance of World class
        interaction:
            instance of Interaction class 
        infection:
            instance of Infection class
        activity_to_groups:
            mapping between an activity and its corresponding groups
        time_config:
            dictionary with temporal configuration to set up the simulation
        min_age_home_alone:
            minimum age of a child to be left alone at home when ill
        stay_at_home_complacency:
            probability that an ill person will not stay at home
        policies:
            policies to be implemented at different time steps
        save_path:
            path to save logger results
        """
        super().__init__(
            world,
            interaction,
            selector,
            activity_to_groups,
            time_config,
            infection_seed,
            leisure,
            min_age_home_alone,
            stay_at_home_complacency,
            policies,
            save_path,
            output_filename,
            light_logger,
        )

    def kid_drags_guardian(self, guardian):
        # not available in box
        pass

    def move_mild_kid_guardian_to_household(self, kid: "Person", activities: List[str]):
        # not available in box
        pass

    def move_mild_ill_to_household(self, person: "Person", activities: List[str]):
        # not available in box
        pass

    def move_people_to_active_subgroups(self, activities: List[str]):
        """
        Sends every person to one subgroup. If a person has a mild illness,
        they stay at home with a certain probability given by stay_at_home_complacency

        Parameters
        ----------
        active_groups:
            list of groups that are active at a time step
        """
        activities = self.apply_activity_hierarchy(activities)
        for person in self.world.people.members:
            if person.dead or person.busy:
                continue
            self.move_to_active_subgroup(activities, person)

    def do_timestep(self):
        """
        Perform a time step in the simulation

        """
        activities = self.timer.activities

        if not activities or len(activities) == 0:
            sim_logger.info("==== do_timestep(): no active groups found. ====")
            return
        if self.policies is not None:
            self.policies.apply_change_probabilities_leisure(
                self.timer.date, self.leisure
            )
        self.move_people_to_active_subgroups(activities,)
        active_groups = self.activities_to_groups(activities)
        group_instances = [
            getattr(self.world, group)
            for group in active_groups
            if group not in ["household_visits", "care_home_visits"]
        ]
        n_people = 0

        for cemetery in self.world.cemeteries.members:
            n_people += len(cemetery.people)
        sim_logger.info(
            f"Date = {self.timer.date}, number of deaths =  {n_people}, number of infected = {len(self.world.people.infected)}"
        )

        if (
            self.policies is not None
            and self.policies.social_distancing
            and self.policies.social_distancing_start
            <= self.timer.date
            < self.policies.social_distancing_end
        ):

            self.interaction.beta = self.policies.apply_social_distancing_policy(
                self.beta_copy, self.timer.now
            )
        else:
            self.interaction.beta = self.beta_copy

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

    def move_to_active_subgroup(
        self, activities: List[str], person: "Person"
    ) -> "Subgroup":
        """
        Given the hierarchy of activities and a person, decide what subgroup  
        should they go to

        Parameters
        ----------
        activities:
            list of activities that take place at a given time step
        person:
            person that is looking for a subgroup to go to
        Returns
        -------
        Subgroup to which person has to go, given the hierarchy of activities
        """
        for activity in activities:
            subgroup = getattr(person, activity)
            if subgroup is not None:
                subgroup.append(person)
            return
        raise SimulatorError(
            "Attention! Some people do not have an activity in this timestep."
        )

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
