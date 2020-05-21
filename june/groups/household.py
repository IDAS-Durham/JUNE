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

    __slots__ = ("area", "communal", "max_size", "n_residents")

    class SubgroupType(IntEnum):
        kids = 0
        young_adults = 1
        adults = 2
        old_adults = 3

    def __init__(self, communal=False, area=None, max_size=np.inf):
        super().__init__()
        self.area = area
        self.communal = communal
        self.max_size = max_size
        self.n_residents = 0

    def add(self, person, subgroup_type=SubgroupType.adults):
        housemates = []
        for mate in self.people:
            if person != mate:
                housemates.append(person)
                person.housemates = housemates
        self[subgroup_type].append(person)
        person.subgroups.residence = self[subgroup_type]
        #subgroups = list(person.subgroups)
        #subgroups[person.ActivityType.residence] = self[subgroup_type]
        #person.subgroups = tuple(subgroups)
        #person.subgroups[person.ActivityType.residence] = self[subgroup_type]

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

