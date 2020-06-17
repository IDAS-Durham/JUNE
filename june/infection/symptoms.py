import random
import sys
from enum import IntEnum

import autofit as af
import numpy as np


class SymptomTag(IntEnum):
    """
    A tag for the symptoms exhibited by a person.

    Higher numbers are more severe.
    0 - 5 correspond to indices in the health index array.
    """

    recovered = -3
    healthy = -2
    exposed = -1
    asymptomatic = 0
    influenza = 1
    pneumonia = 2
    hospitalised = 3
    intensive_care = 4
    dead = 5

    @classmethod
    def from_string(cls, string: str) -> "SymptomTag":
        for item in SymptomTag:
            if item.name == string:
                return item
        raise AssertionError(
            f"{string} is not the name of a SymptomTag"
        )


class Symptoms:
    def __init__(self, health_index=None):
        self.health_index = list() if health_index is None else health_index
        self.tag = SymptomTag.exposed
        self.max_severity = random.random()
        self._severity = 0.0

    def update_severity_from_delta_time(self, time):
        raise NotImplementedError()

    def is_recovered(self):
        return self.tag == SymptomTag.recovered

    def make_tag(self):
        if self.severity <= 0.0 or len(self.health_index) == 0:
            return SymptomTag.recovered
        index = np.searchsorted(self.health_index, self.severity)
        return SymptomTag(index)

    @property
    def severity(self):
        return self._severity

    @severity.setter
    def severity(self, severity):
        self._severity = severity

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
    @property
    def severity(self):
        return 0.0

    def __init__(self, health_index=0., recovery_rate=0.2):
        super().__init__(health_index=health_index)

        self.recovery_rate = recovery_rate
        self.severity = 0.

    def update_severity_from_delta_time(self, delta_time):
        pass

    def is_recovered(self, delta_time):
        prob_recovery = 1.0 - np.exp(-self.recovery_rate * delta_time)
        return np.random.rand() <= prob_recovery
