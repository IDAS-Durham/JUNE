import random
import sys
from enum import IntEnum

import autofit as af
import numpy as np


class SymptomTags(IntEnum):
    healthy = 0
    infected = 1
    asymptomatic = 2
    influenza = 3
    pneumonia = 4
    hospitalised = 5
    intensive_care = 6
    dead = 7
    recovered = 8


class Symptoms:
    def __init__(self, health_index=None):
        self.health_index = list() if health_index is None else health_index
        self.tag = SymptomTags.infected
        self.max_severity = random.random()
        self.severity = 0.0

    def update_severity_from_delta_time(self, time):
        raise NotImplementedError()

    def is_recovered(self):
        return self.tag == SymptomTags.recovered

    def make_tag(self):
        if self.severity <= 0.0 or len(self.health_index) == 0:
            return SymptomTags.recovered
        index = np.searchsorted(self.health_index, self.severity)
        return SymptomTags(index + 2)

    @classmethod
    def object_from_config(cls):
        """
        Loads the default Symptoms class from the general.ini config file and returns the class 
        as object (not as an instance). This is used to set up the epidemiology model in world.py 
        via configs if an input is not provided.
        """
        classname_str = af.conf.instance.general.get("epidemiology", "symptoms_class", str)
        return getattr(sys.modules[__name__], classname_str)


class SymptomsHealthy(Symptoms):
    def __init__(self, health_index=0., recovery_rate=0.2):
        super().__init__(health_index=health_index)

        self.recovery_rate = recovery_rate
        self.severity = 0.

    def update_severity_from_delta_time(self, delta_time):
        pass

    def is_recovered(self, delta_time):
        prob_recovery = 1.0 - np.exp(-self.recovery_rate * delta_time)
        return np.random.rand() <= prob_recovery


class SymptomsConstant(Symptoms):
    def __init__(self, health_index=None, recovery_rate=0.2):
        super().__init__(health_index=health_index)
        self.recovery_rate = recovery_rate
        self.severity = self.max_severity

    def update_severity_from_delta_time(self, delta_time):
        if np.random.rand() <= 1.0 - np.exp(-self.recovery_rate * delta_time):
            self.tag = SymptomTags.recovered


class SymptomsGaussian(Symptoms):
    # TODO: Add recovery_theshold for recovery, and check parameters to find days to recover
    def __init__(self, health_index=None, mean_time=1.0, sigma_time=3.0, recovery_rate=0.05):
        super().__init__(health_index=health_index)
        self.mean_time = max(0.0, mean_time)
        self.sigma_time = max(0.001, sigma_time)
        self.max_severity = random.random()
        self.recovery_rate = recovery_rate

    def update_severity_from_delta_time(self, delta_time):
        if np.random.rand() <= 1.0 - np.exp(-self.recovery_rate * delta_time):
            self.tag = SymptomTags.recovered
        else:
            dt = delta_time - self.mean_time
            self.severity = self.max_severity * np.exp(-(dt ** 2) / self.sigma_time ** 2)
            self.tag = self.make_tag()


class SymptomsStep(Symptoms):
    def __init__(self, health_index=None, time_offset=2.0, end_time=5.0):

        super().__init__(health_index)
        self.time_offset = max(0.0, time_offset)
        self.end_time = max(0.0, end_time)
        self.max_severity = random.random()

    def update_severity_from_delta_time(self, delta_time):
        if self.time_offset <= delta_time <= self.end_time:
            self.severity = self.max_severity
        else:
            self.severity = 0.0
        self.tag = self.make_tag()


class SymptomsTanh(Symptoms):
    def __init__(self, health_index=0., max_time=2.0, onset_time=0.5, end_time=15.0):

        super().__init__(health_index)

        self.max_time = max(0.0, max_time)
        self.onset_time = max(0.0, onset_time)
        self.end_time = max(0.0, end_time)
        self.delta_onset = self.max_time - self.onset_time
        self.delta_end = self.end_time - self.max_time

    def update_severity_from_delta_time(self, delta_time):
        # TODO : These have both cropped up in the recent project history, which is correct?
        if delta_time <= self.max_time:
            self.severity = (
                                    1.0
                                    + np.tanh(np.pi * (delta_time - self.onset_time) / self.delta_onset)
                            ) / 2.0
        else:
            self.severity = (
                                    1.0 + np.tanh(np.pi * (self.end_time - delta_time) / self.delta_end)
                            ) / 2.0
        self.severity *= self.max_severity
        self.tag = self.make_tag()
