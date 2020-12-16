import logging
from typing import Optional, List
from itertools import chain
import datetime

from june.interaction import Interaction
from june.groups.group.interactive import InteractiveGroup
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
            checkpoint_save_dates: List[datetime.date] = None,
            record: "Record" = None,
            checkpoint_save_path: str = None,
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
        super().__init__(
            world=world,
            interaction=interaction,
            timer=timer,
            activity_manager=activity_manager,
            infection_selector=infection_selector,
            infection_seed=infection_seed,
            record=record,
            checkpoint_save_dates=checkpoint_save_dates,
            checkpoint_save_path = checkpoint_save_path
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
