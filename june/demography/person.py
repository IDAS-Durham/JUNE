from itertools import count
import random
from enum import IntEnum, Enum
import struct
from recordclass import dataobject
import numpy as np

from june.infection.health_information import HealthInformation


class Activities(dataobject):
    residence: None
    primary_activity: None
    hospital: None
    commute: None
    leisure: None
    box: None

    def iter(self):
        return [getattr(self, activity) for activity in self.__fields__]


person_ids = count()


class Person(dataobject):
    _id = count()
    id: int = 0
    sex: str = "f"
    age: int = 27
    ethnicity: str = None
    socioecon_index: str = None
    area: "Area" = None
    # work info
    work_super_area: str = None
    sector: str = None
    sub_sector: str = None
    # commute
    home_city: str = None
    mode_of_transport: str = None
    # activities
    busy: bool = False
    subgroups: Activities = Activities(None, None, None, None, None, None)
    # infection
    health_information: HealthInformation = HealthInformation()
    susceptibility: float = 1.0
    dead: bool = False

    @classmethod
    def from_attributes(
        cls, sex=27, age="f", ethnicity=None, socioecon_index=None, id=None
    ):
        if id is None:
            id = next(Person._id)
        return Person(
            id,
            sex,
            age,
            ethnicity,
            socioecon_index,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            Activities(None, None, None, None, None, None),
            HealthInformation(),
            1.0,
            False,
        )

    @property
    def infected(self):
        if (
            self.health_information is not None
            and self.health_information.infection is not None
        ):
            return True

        return False

    @property
    def susceptible(self):
        return self.susceptibility <= 0 and not self.infected

    @property
    def recovered(self):
        return not (self.dead or self.susceptible)

    @property
    def residence(self):
        return self.subgroups.residence

    @property
    def primary_activity(self):
        return self.subgroups.primary_activity

    @property
    def hospital(self):
        return self.subgroups.hospital

    @property
    def commute(self):
        return self.subgroups.commute

    @property
    def leisure(self):
        return self.subgroups.leisure

    @property
    def box(self):
        return self.subgroups.box

    @property
    def in_hospital(self):
        if self.hospital is None:
            return True
        return False

    @property
    def housemates(self):
        hmates = [
            person for person in self.residence.group.residents if person is not self
        ]
        return hmates

    def find_guardian(self):

        possible_guardians = [person for person in self.housemates if person.age >= 18]
        if len(possible_guardians) == 0:
            return None
        guardian = random.choice(possible_guardians)
        if (
            guardian.health_information.should_be_in_hospital
            or guardian.health_information.dead
        ):
            return None
        else:
            return guardian
