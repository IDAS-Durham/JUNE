from enum import IntEnum


import numpy as np
import random

from june.groups.group import Group, Supergroup
from enum import IntEnum
from typing import List


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
        for mate in self.people:
            if person != mate:
                mate.housemates.append(person)
                person.housemates.append(mate)
        self[subgroup_type].append(person)
        person.subgroups[person.ActivityType.residence] = self[subgroup_type]

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

    __slots__ = "members"

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

    def erase_people_from_groups_and_subgroups(self):
        """
        Sets all attributes in self.references_to_people to None for all groups.
        Erases all people from subgroups.
        """
        for group in self:
            for person in group.people:
                person.housemates.clear()
            for subgroup in group.subgroups:
                subgroup._people.clear()
                subgroup.group = None

