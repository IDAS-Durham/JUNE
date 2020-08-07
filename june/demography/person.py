from itertools import count
import random
from enum import IntEnum, Enum
import struct
from recordclass import dataobject
import numpy as np
from june.infection.health_information import HealthInformation
from june.commute import ModeOfTransport


class Activities(dataobject):
    residence: None
    primary_activity: None
    medical_facility: None
    commute: None
    rail_travel: None
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
    lockdown_status: str = None
    comorbidity: str = None
    # commute
    home_city: str = None
    mode_of_transport: ModeOfTransport = None
    # rail travel
    # activities
    busy: bool = False
    subgroups: Activities = Activities(None, None, None, None, None, None, None)
    health_information: HealthInformation = None
    # infection
    susceptibility: float = 1.0
    dead: bool = False

    @classmethod
    def from_attributes(
        cls,
        sex="f",
        age=27,
        ethnicity=None,
        socioecon_index=None,
        id=None,
        comorbidity=None,
    ):
        if id is None:
            id = next(Person._id)
        return Person(
            id=id,
            sex=sex,
            age=age,
            ethnicity=ethnicity,
            socioecon_index=socioecon_index,
            # IMPORTANT, these objects need to be recreated, otherwise the default
            # is always the same object !!!!
            comorbidity=comorbidity,
            subgroups=Activities(None, None, None, None, None, None, None),
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
        return self.susceptibility > 0.0 and not self.infected and not self.dead

    @property
    def recovered(self):
        return not (self.dead or self.susceptible or self.infected)

    @property
    def residence(self):
        return self.subgroups.residence

    @property
    def primary_activity(self):
        return self.subgroups.primary_activity

    @property
    def medical_facility(self):
        return self.subgroups.medical_facility

    @property
    def commute(self):
        return self.subgroups.commute

    @property
    def rail_travel(self):
        return self.subgroups.rail_travel

    @property
    def leisure(self):
        return self.subgroups.leisure

    @property
    def box(self):
        return self.subgroups.box

    @property
    def hospitalised(self):
        try:
            return all(
                [
                    self.medical_facility.group.spec == "hospital",
                    self.medical_facility.subgroup_type
                    == self.medical_facility.group.SubgroupType.patients,
                ]
            )
        except AttributeError:
            return False

    @property
    def intensive_care(self):
        if (
            self.hospital is not None
            and self.hospital.subgroup_type
            == self.hospital.group.SubgroupType.icu_patients
        ):
            return True
        return False

    @property
    def housemates(self):
        if self.residence.group.spec == "care_home":
            return []
        return self.residence.group.residents

    def find_guardian(self):
        possible_guardians = [person for person in self.housemates if person.age >= 18]
        if not possible_guardians:
            return None
        guardian = random.choice(possible_guardians)
        if (
            guardian.health_information is not None
            and guardian.health_information.should_be_in_hospital
        ) or guardian.dead:
            return None
        else:
            return guardian

    @property
    def infection(self):
        if self.health_information is None:
            return None
        else:
            return self.health_information.infection

    @property
    def symptoms(self):
        if self.health_information is None:
            return None
        else:
            return self.health_information.infection.symptoms
