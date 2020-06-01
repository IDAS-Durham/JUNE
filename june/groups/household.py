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

    __slots__ = ("area", "type", "max_size", "n_residents", "residents", "relatives")

    class SubgroupType(IntEnum):
        kids = 0
        young_adults = 1
        adults = 2
        old_adults = 3

    def __init__(self, type=None, area=None, max_size=np.inf, contact_matrices=None):
        """
        Type should be on of ["family", "student", "young_adults", "old", "other", "nokids", "ya_parents", "communal"].
        Relatives is a list of people that are related to the family living in the household
        """
        super().__init__()
        self.area = area
        self.type = type
        self.residents = tuple()
        self.max_size = max_size
        self.n_residents = 0
        self.relatives = None
        self.contact_matrices = contact_matrices

    def add(self, person, subgroup_type=SubgroupType.adults):
        self[subgroup_type].append(person)
        self.residents = tuple((*self.residents, person))
        person.subgroups.residence = self[subgroup_type]

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

