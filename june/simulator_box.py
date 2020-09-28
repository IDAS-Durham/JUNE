import logging
from typing import Optional, List
from itertools import chain
import datetime

from june.interaction import Interaction, InteractiveGroup
from june import paths
from june.activity import ActivityManagerBox
from june.interaction import Interaction
from june.simulator import Simulator
from june.world import World
from june.infection import InfectionSelector
from june.policy import MedicalCarePolicies

default_config_filename = paths.configs_path / "config_example.yaml"

sim_logger = logging.getLogger(__name__)


class SimulatorError(BaseException):
    pass


class SimulatorBox(Simulator):
    ActivityManager = ActivityManagerBox

    def __init__(
            self,
            world: World,
            interaction: Interaction,
            timer,
            activity_manager,
            infection_selector: InfectionSelector = None,
            infection_seed: Optional["InfectionSeed"] = None,
            checkpoint_dates: List[datetime.date] = None,
            logger: "Logger" = None,
            comment: str = None,
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
        policies:
            policies to be implemented at different time steps
        """
        self.beta_copy = interaction.beta

        super().__init__(
            world=world,
            interaction=interaction,
            timer=timer,
            activity_manager=activity_manager,
            infection_selector=infection_selector,
            infection_seed=infection_seed,
            logger=logger,
            comment=comment,
            checkpoint_dates=checkpoint_dates,
        )

    def do_timestep(self):
        """
        Perform a time step in the simulation

        """
        activities = self.timer.activities

        if not activities or len(activities) == 0:
            sim_logger.info("==== do_timestep(): no active groups found. ====")
            return

        self.activity_manager.do_timestep()

        policies = self.activity_manager.policies

        active_groups = self.activity_manager.activities_to_super_groups(activities)
        group_instances = [
            getattr(self.world, group)
            for group in active_groups
            if group not in ["household_visits", "care_home_visits"]
        ]

        if (
                policies is not None
                and policies.social_distancing
                and policies.social_distancing_start
                <= self.timer.date
                < policies.social_distancing_end
        ):

            self.interaction.beta = policies.apply_social_distancing_policy(
                self.beta_copy, self.timer.now
            )
        else:
            self.interaction.beta = self.beta_copy

        n_people = 0

        for cemetery in self.world.cemeteries.members:
            n_people += len(cemetery.people)
        sim_logger.info(
            f"Date = {self.timer.date}, number of deaths =  {n_people}, number of infected = {len(self.world.people.infected)}"
        )
        infected_ids = []
        first_person_id = self.world.people[0].id
        for group_type in group_instances:
            for group in group_type.members:
                int_group = InteractiveGroup(group, None)
                n_people += int_group.size
                if int_group.must_timestep:
                    new_infected_ids = self.interaction.time_step_for_group(
                        self.timer.duration, int_group
                    )
                    if new_infected_ids:
                        n_infected = len(new_infected_ids)
                        if self.logger is not None:
                            self.logger.accumulate_infection_location(
                                group.spec, n_infected
                            )
                        # assign blame of infections
                        tprob_norm = sum(int_group.transmission_probabilities)
                        for infector_id in chain.from_iterable(
                                int_group.infector_ids):
                            infector = self.world.people[infector_id - first_person_id]
                            infector.infection.number_of_infected += (
                                n_infected
                                * infector.infection.transmission.probability
                                / tprob_norm
                            )
                    infected_ids += new_infected_ids
        people_to_infect = [self.world.people[idx - first_person_id] for idx in infected_ids]
        if n_people != len(self.world.people):
            raise SimulatorError(
                f"Number of people active {n_people} does not match "
                f"the total people number {len(self.world.people.members)}"
            )
        # infect people
        if self.infection_selector:
            for person in people_to_infect:
                self.infection_selector.infect_person_at_time(person, self.timer.now)
        self.update_health_status(time=self.timer.now, duration=self.timer.duration)
        if self.logger:
            self.logger.log_infection_location(self.timer.date)
            self.logger.log_hospital_capacity(self.timer.date, self.world.hospitals)
        self.clear_world()

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
        if self.activity_manager.policies is not None:
            medical_care_policies = MedicalCarePolicies.get_active_policies(
                policies=self.activity_manager.policies, date=self.timer.date
            )
        for person in self.world.people.infected:
            previous_tag = person.infection.tag
            new_status = person.infection.update_health_status(time, duration)
            ids.append(person.id)
            symptoms.append(person.infection.tag.value)
            n_secondary_infections.append(person.infection.number_of_infected)
            # Take actions on new symptoms
            if self.activity_manager.policies is not None:
                medical_care_policies.apply(person=person)
            if new_status == "recovered":
                self.recover(person)
            elif new_status == "dead":
                self.bury_the_dead(person)
        if self.logger:
            self.logger.log_infected(
                self.timer.date, ids, symptoms, n_secondary_infections
            )
