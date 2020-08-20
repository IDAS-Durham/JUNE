from enum import IntEnum

import numpy as np
import yaml

from june import paths
from june.infection.health_index import HealthIndexGenerator
from june.infection.health_information import HealthInformation
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
    person, and their symptoms trajectory.
    """

    __slots__ = (
        "number_of_infected",
        "start_time",
        "last_time_updated",
        "transmission",
        "symptoms",
        "infection_probability",
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
        self.last_time_updated = start_time
        self.transmission = transmission
        self.symptoms = symptoms
        self.infection_probability = 0.0
        self.number_of_infected = 0.0

    def update_at_time(self, time: float):
        """
        Updates symptoms and infectousness 

        Parameters
        ----------
        time:
            time elapsed from time of infection
        """
        if self.last_time_updated <= time:
            time_from_infection = time - self.start_time
            self.last_time_updated = time
            self.transmission.update_probability_from_delta_time(
                time_from_infection=time_from_infection
            )
            self.symptoms.update_severity_from_delta_time(
                time_from_infection=time_from_infection
            )
            self.infection_probability = self.transmission.probability

    @property
    def tag(self):
        return self.infection.symptoms.tag

    @property
    def time_of_infection(self):
        return self.infection.start_time

    @property
    def should_be_in_hospital(self) -> bool:
        return self.tag in (SymptomTag.hospitalised, SymptomTag.intensive_care)

    @property
    def infected_at_home(self) -> bool:
        return self.infected and not (self.dead or self.should_be_in_hospital)

    @property
    def is_dead(self) -> bool:
        return self.tag in dead_tags

    @property
    def time_of_symptoms_onset(self):
        return self.infection.symptoms.time_of_symptoms_onset

    def update_health_status(self, time, delta_time):
        self.infection.update_at_time(time + delta_time)
        if self.infection.symptoms.is_recovered():
            self.recovered = True

    def set_recovered(self, time):
        self.recovered = True
        self.infected = False
        self.susceptible = False
        self.set_length_of_infection(time)
        self.infection = None

    def set_dead(self, time):
        self.dead = True
        self.infected = False
        self.susceptible = False
        self.set_length_of_infection(time)
        self.infection = None

    def transmission_probability(self, time):
        if self.infection is not None:
            return 0.0
        return self.infection.transmission_probability(time)

    def symptom_severity(self, severity):
        if self.infection is None:
            return 0.0
        return self.infection.symptom_severity(severity)

    def set_length_of_infection(self, time):
        self.length_of_infection = time - self.time_of_infection
