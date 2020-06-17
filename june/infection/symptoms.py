import random
import sys
from enum import IntEnum

import autofit as af


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

    def update_severity_from_delta_time(self, time):
        raise NotImplementedError()

    def is_recovered(self):
        return self.tag == SymptomTag.recovered

    @classmethod
    def object_from_config(cls):
        """
        Loads the default Symptoms class from the general.ini config file and returns the class 
        as object (not as an instance). This is used to set up the epidemiology model in world.py 
        via configs if an input is not provided.
        """
        classname_str = af.conf.instance.general.get("epidemiology", "symptoms_class", str)
        return getattr(sys.modules[__name__], classname_str)
