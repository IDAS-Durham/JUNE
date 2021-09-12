from enum import IntEnum

import numpy as np
import yaml
from zlib import adler32

from june import paths
from .health_index.health_index import HealthIndexGenerator
from .symptoms import Symptoms, SymptomTag
from .trajectory_maker import TrajectoryMakers
from .transmission import TransmissionConstant, TransmissionGamma
from .transmission_xnexp import TransmissionXNExp
from .trajectory_maker import CompletionTime


class Infection:
    """
    The infection class combines the transmission (infectiousness profile) of the infected
    person, and their symptoms trajectory. We also keep track of how many people someone has
    infected, which is useful to compute R0. The infection probability is updated at every
    time step, according to an infectivity profile.
    """

    __slots__ = (
        "start_time",
        "transmission",
        "symptoms",
        "time_of_testing",
    )
    _infection_id = None

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
        self.time_of_testing = None

    @classmethod  # this could be a property but it is complicated (needs meta classes)
    def infection_id(cls):
        # this creates a unique id for each inherited class
        if not cls._infection_id:
            cls._infection_id = adler32(cls.__name__.encode("ascii"))
        return cls._infection_id

    @classmethod
    def immunity_ids(cls):
        """
        Ids of the infections that upon recovery this infection gives immunity to.
        """
        return (cls.infection_id(),)

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


class Covid19(Infection):
    @classmethod
    def immunity_ids(cls):
        return (cls.infection_id(), B117.infection_id())


class B117(Infection):
    @classmethod
    def immunity_ids(cls):
        return (cls.infection_id(), Covid19.infection_id())

class B16172(Infection):
    @classmethod
    def immunity_ids(cls):
        return (cls.infection_id(), Covid19.infection_id(), B117.infection_id())
