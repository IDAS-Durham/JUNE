import logging
from typing import Optional

from june import paths
from june.groups.activity.activity_manager_box import ActivityManagerBox
from june.interaction import Interaction
from june.simulator import Simulator
from june.world import World

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
            infection_seed: Optional["InfectionSeed"] = None,
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
        policies:
            policies to be implemented at different time steps
        save_path:
            path to save logger results
        """
        self.beta_copy = interaction.beta

        super().__init__(
            world=world,
            interaction=interaction,
            timer=timer,
            activity_manager=activity_manager,
            infection_seed=infection_seed,
            save_path=save_path,
            output_filename=output_filename,
            light_logger=light_logger,
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

        active_groups = self.activity_manager.activities_to_groups(activities)
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
