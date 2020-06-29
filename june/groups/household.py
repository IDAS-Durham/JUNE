from enum import IntEnum


import numpy as np
import random
import h5py
import time

from june.groups.group import Group, Supergroup
from enum import IntEnum
from typing import List
from recordclass import dataobject


class Household(Group):
    """
    The Household class represents a household and contains information about 
    its residents.
    We assume four subgroups:
    0 - kids
    1 - young adults
    2 - adults
    3 - old adults
    """

    __slots__ = (
        "area",
        "type",
        "max_size",
        "n_residents",
        "residents",
        "relatives_in_care_homes",
        "relatives_in_households",
        "quarantine_starting_date",
    )

    class SubgroupType(IntEnum):
        kids = 0
        young_adults = 1
        adults = 2
        old_adults = 3

    def __init__(self, type=None, area=None, max_size=np.inf):
        """
        Type should be on of ["family", "student", "young_adults", "old", "other", "nokids", "ya_parents", "communal"].
        Relatives is a list of people that are related to the family living in the household
        """
        super().__init__()
        self.area = area
        self.type = type
        self.quarantine_starting_date = None
        self.relatives_in_care_homes = None
        self.relatives_in_households = None
        self.max_size = max_size
        self.n_residents = 0
        self.residents = tuple()

    def add(self, person, subgroup_type=SubgroupType.adults, activity="residence"):
        if activity == "leisure":
            if person.age < 18:
                subgroup = self.SubgroupType.kids
            elif person.age <= 35:
                subgroup = self.SubgroupType.young_adults
            elif person.age < 65:
                subgroup = self.SubgroupType.adults
            else:
                subgroup = self.SubgroupType.old_adults
            person.subgroups.leisure = self[subgroup]
            self[subgroup].append(person)
        elif activity == "residence":
            self[subgroup_type].append(person)
            self.residents = tuple((*self.residents, person))
            person.subgroups.residence = self[subgroup_type]
        else:
            raise NotImplementedError(f"Activity {activity} not supported in household")

    def get_leisure_subgroup(self, person):
        if person.age < 18:
            return self.subgroups[self.SubgroupType.kids]
        elif person.age <= 35:
            return self.subgroups[self.SubgroupType.young_adults]
        elif person.age < 65:
            return self.subgroups[self.SubgroupType.adults]
        else:
            return self.subgroups[self.SubgroupType.old_adults]

    @property
    def kids(self):
        return self.subgroups[self.SubgroupType.kids]

    @property
    def young_adults(self):
        return self.subgroups[self.SubgroupType.young_adults]

    @property
    def adults(self):
        return self.subgroups[self.SubgroupType.adults]

    @property
    def old_adults(self):
        return self.subgroups[self.SubgroupType.old_adults]

    def quarantine(self, time, quarantine_days):
        if self.type == "communal":
            return False
        if self.quarantine_starting_date:
            if (
                self.quarantine_starting_date
                < time
                < self.quarantine_starting_date + quarantine_days
            ):
                return True
        return False


class Households(Supergroup):
    """
    Contains all households for the given area, and information about them.
    """

    def __init__(self, households: List[Household]):
        super().__init__()
        self.members = households

    def __add__(self, households: "Households"):
        """
        Adding two households instances concatenates the members
        list.

        Parameters
        ----------
        households:
            instance of Households to sum with.
        """
        self.members += households.members
        return self
