from enum import IntEnum

import numpy as np
import yaml

from june import paths
from june.infection.health_index.health_index import HealthIndexGenerator
from june.infection.symptoms import Symptoms, SymptomTag
from june.infection.trajectory_maker import TrajectoryMakers
from june.infection.transmission import TransmissionConstant, TransmissionGamma
from june.infection.transmission_xnexp import TransmissionXNExp
from june.infection.trajectory_maker import CompletionTime

default_transmission_config_path = (
    paths.configs_path / "defaults/transmission/nature.yaml"
)
default_trajectories_config_path = (
    paths.configs_path / "defaults/symptoms/trajectories.yaml"
)


class Infection:
    """
    The infection class combines the transmission (infectiousness profile) of the infected
    person, and their symptoms trajectory. We also keep track of how many people someone has
    infected, which is useful to compute R0. The infection probability is updated at every 
    time step, according to an infectivity profile.
    """

    __slots__ = (
        "number_of_infected",
        "start_time",
        "transmission",
        "symptoms",
        "time_of_testing",
    )

    def __init__(
        self, transmission: "Transmission", symptoms: "Symptoms", start_time: float = -1
    ):
        """
        Parameters
        ----------
        transmission:
            instance of the class that controls the infectiousness profile
        symptoms:
            instance of the class that controls the symptoms' evolution
        start_time:
            time at which the person is infected
        """
        self.start_time = start_time
        self.transmission = transmission
        self.symptoms = symptoms
        self.number_of_infected = 0.0
        self.time_of_testing = None

    def update_health_status(self, time, delta_time):
        """
        Updates the infection probability and symptoms of the person's infection
        given the simulation time. Returns the new status of the person.

        Parameters:
        -----------
        time: float
            total time since the beginning of the simulation (in days)
        delta_time: float
            duration of the time step.

        Returns:
        --------
        status: str
            new status of the person. one of ``['recovered', 'dead', 'infected']``
        """
        self.update_symptoms_and_transmission(time + delta_time)
        if self.symptoms.recovered:
            status = "recovered"
        elif self.symptoms.dead:
            status = "dead"
        else:
            status = "infected"
        return status

    def update_symptoms_and_transmission(self, time: float):
        """
        Updates the infection's symptoms and transmission probability.
        Parameters
        ----------
        time:
            time elapsed (in days) from time of infection
        """
        time_from_infection = time - self.start_time
        self.transmission.update_infection_probability(
            time_from_infection=time_from_infection
        )
        self.symptoms.update_trajectory_stage(time_from_infection=time_from_infection)

    def length_of_infection(self, time):
        return time - self.time_of_infection

    @property
    def tag(self):
        return self.symptoms.tag

    @property
    def max_tag(self):
        return self.symptoms.max_tag

    @property
    def time_of_infection(self):
        return self.start_time

    @property
    def should_be_in_hospital(self) -> bool:
        return self.tag in (SymptomTag.hospitalised, SymptomTag.intensive_care)

    @property
    def infected_at_home(self) -> bool:
        return self.infected and not (self.dead or self.should_be_in_hospital)

    @property
    def dead(self) -> bool:
        return self.symptoms.dead

    @property
    def time_of_symptoms_onset(self):
        return self.symptoms.time_of_symptoms_onset

    @property
    def infection_probability(self):
        return self.transmission.probability
