from itertools import count
import random
from enum import IntEnum, Enum
from june.infection import SymptomTags
import struct
from recordclass import dataobject

# import june.groups.household
import numpy as np


class HealthInformation:
    __slots__ = (
        "susceptibility",
        "susceptible",
        "infected",
        "infection",
        "recovered",
        "dead",
        "number_of_infected",
        "maximal_symptoms",
        "maximal_symptoms_time",
        "maximal_symptoms_tag",
        "time_of_infection",
        "group_type_of_infection",
        "length_of_infection",
        "infecter")

    def __init__(self):
        self.susceptibility = 1.0
        self.susceptible = True
        self.infected = False
        self.infection = None
        self.recovered = False
        self.dead = False
        self.number_of_infected = 0
        self.maximal_symptoms = 0
        self.maximal_symptoms_time = -1
        self.maximal_symptoms_tag = None
        self.time_of_infection = -1
        self.group_type_of_infection = None
        self.length_of_infection = -1
        self.infecter = None

    def set_infection(self, infection):
        self.infection = infection
        self.infected = True
        self.susceptible = False
        self.susceptibility = 0.0
        self.time_of_infection = infection.start_time

    @property
    def tag(self):
        if self.infection is not None:
            return self.infection.symptoms.tag
        return None

    @property
    def must_stay_at_home(self) -> bool:
        return self.tag in (SymptomTags.influenza, SymptomTags.pneumonia)

    @property
    def should_be_in_hospital(self) -> bool:
        return self.tag in (SymptomTags.hospitalised, SymptomTags.intensive_care)

    @property
    def infected_at_home(self) -> bool:
        return self.infected and not (self.dead or self.should_be_in_hospital)

    @property
    def is_dead(self) -> bool:
        return self.tag == SymptomTags.dead

    def update_health_status(self, time, delta_time):
        if self.infected:
            if self.infection.symptoms.is_recovered():
                self.recovered = True
            else:
                self.infection.update_at_time(time + delta_time)

    def set_recovered(self, time):
        self.recovered = True
        self.infected = False
        self.susceptible = False
        self.susceptibility = 0.0
        self.set_length_of_infection(time)
        self.infection = None

    def set_dead(self, time):
        self.dead = True
        self.infected = False
        self.susceptible = False
        self.susceptibility = 0.0
        self.set_length_of_infection(time)
        self.infection = None

    def get_symptoms_tag(self, symptoms):
        return self.infection.symptoms.tag

    def transmission_probability(self, time):
        if self.infection is not None:
            return 0.0
        return self.infection.transmission_probability(time)

    def symptom_severity(self, severity):
        if self.infection is None:
            return 0.0
        return self.infection.symptom_severity(severity)

    def update_symptoms(self, time):  # , symptoms, time):
        if self.infection.symptoms.severity > self.maximal_symptoms:
            self.maximal_symptoms = self.infection.symptoms.severity
            self.maximal_symptoms_tag = self.get_symptoms_tag(self.infection.symptoms)
            self.maximal_symptoms_time = time - self.time_of_infection

    def update_infection_data(self, time, group_type=None, infecter=None):
        self.time_of_infection = time
        if group_type is not None:
            self.group_type_of_infection = group_type
        if infecter is not None:
            self.infecter = infecter

    def set_length_of_infection(self, time):
        self.length_of_infection = time - self.time_of_infection

    def increment_infected(self):
        self.number_of_infected += 1


# class Person:
#    #_id = count()
#    __slots__ = (
#        #"id",
#        "age",
#        "sex",
#        "ethnicity",
#        "socioecon_index",
#        "area",
#        "work_super_area",
#        "mode_of_transport",
#        "home_city",
#        "sector",
#        "sub_sector",
#        "busy",
#        #"attributes",
#        "housemates",
#        "subgroups",
#        ##"health_information",
#    )
#
#    class ActivityType(IntEnum):
#        """
#        Defines the indices of the subgroups a person belongs to
#        """
#
#        residence = 0
#        primary_activity = 1
#        hospital = 2
#        commute = 3
#        leisure = 4
#        box = 5
#
#    def __init__(
#        self,
#        age=-1,
#        sex=None,
#        ethnicity=None,
#        socioecon_index=None,
#        area=None,
#        work_super_area=None,
#        sector="asdasd",
#        sub_sector="Q",
#        home_city = "Manchester",
#        busy=False,
#        subgroups=(None, None, None, None, None),
#        ):
#        """
#        Inputs:
#        """
#        #self.id = next(self._id)
#        # biological attributes
#        #self.attributes = (sex, age, ethnicity, socioecon_index)
#        self.age = age
#        self.sex = sex
#        self.ethnicity = ethnicity
#        self.socioecon_index = socioecon_index
#        # geo-graphical attributes
#        self.area = area
#        self.work_super_area = work_super_area
#        self.housemates = None
#        ### primary activity attributes
#        self.mode_of_transport = "bus"#None#mode_of_transport
#        self.subgroups = subgroups
#        self.sector = sector
#        self.sub_sector = sub_sector
#        self.home_city = home_city
#        ##self.health_information = HealthInformation()
#        self.busy = busy
#
#    @property
#    def residence(self):
#        return self.subgroups[self.ActivityType.residence]
#
#    @property
#    def primary_activity(self):
#        return self.subgroups[self.ActivityType.primary_activity]
#
#    @property
#    def hospital(self):
#        return self.subgroups[self.ActivityType.hospital]
#
#    @property
#    def commute(self):
#        return self.subgroups[self.ActivityType.commute]
#
#    @property
#    def leisure(self):
#        return self.subgroups[self.ActivityType.leisure]
#
#    @property
#    def box(self):
#        return self.subgroups[self.ActivityType.box]
#
#    @property
#    def in_hospital(self):
#        if self.hospital is None:
#            return True
#        return False
#
#    def find_guardian(self):
#
#        possible_guardians = [person for person in self.housemates if person.age >= 18]
#        if len(possible_guardians) == 0:
#            return None
#        guardian = random.choice(possible_guardians)
#        if (
#            guardian.health_information.should_be_in_hospital
#            or guardian.health_information.dead
#        ):
#            return None
#        else:
#            return guardian

class Activities(dataobject):
    residence: None
    primary_activity: None
    hospital: None
    commute: None
    leisure: None
    box: None


class Person(dataobject):
    _id = count()
    class ActivityType(IntEnum):
        """
        Defines the indices of the subgroups a person belongs to
        """

        residence = 0
        primary_activity = 1
        hospital = 2
        commute = 3
        leisure = 4
        box = 5

    # attributes: tuple
    id: int
    sex: str
    age: int
    ethnicity: str
    socioecon_index: str
    area: None
    work_super_area: str
    sector: str
    sub_sector: str
    home_city: str
    busy: bool
    subgroups: Activities
    housemates: tuple
    #health_information: HealthInformation

    @classmethod
    def from_attributes(cls, sex, age, ethnicity, socioecon_index):
        return Person(
            next(Person._id),
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
            #(None, None, None, None, None, None),
            Activities(None, None, None, None, None, None),#(None, None, None, None, None),
            None,
            #HealthInformation(),
        )

    @property
    def residence(self):
        #return self.subgroups[self.ActivityType.residence]
        return self.subgroups.residence

    @property
    def primary_activity(self):
        #return self.subgroups[self.ActivityType.primary_activity]
        return self.subgroups.primary_activity

    @property
    def hospital(self):
        #return self.subgroups[self.ActivityType.hospital]
        return self.subgroups.hospital

    @property
    def commute(self):
        #return self.subgroups[self.ActivityType.commute]
        return self.subgroups.commute

    @property
    def leisure(self):
        #return self.subgroups[self.ActivityType.leisure]
        return self.subgroups.leisure

    @property
    def box(self):
        #return self.subgroups[self.ActivityType.box]
        return self.subgroups.box

    @property
    def in_hospital(self):
        if self.hospital is None:
            return True
        return False

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
