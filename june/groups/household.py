from itertools import count

import numpy as np

from june.groups.group import Group
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
    __slots__ = "area", "household_composition", "communal", "max_size"

    _id = count()

    class GroupType(IntEnum):
        kids = 0
        young_adults = 1
        adults = 2
        old_adults = 3

    def __init__(self, composition=None, communal=False, area=None, max_size=np.inf):
        house_id = next(self._id)
        super().__init__(f"Household_{house_id}", "household")
        self.area = area
        self.household_composition = composition
        self.communal = communal
        self.max_size = max_size

    def add(self, person, qualifier=GroupType.adults):
        super().add(person, qualifier)
        person.household = self

    def set_active_members(self):
        for grouping in self.subgroups:
            for person in grouping.people:
                if (person.active_group is None and
                        person.health_information.tag != "intensive care" and
                        person.health_information.tag != "hospitalised"):
                    person.active_group = "household"


class Households:
    """
    Contains all households for the given area, and information about them.
    """

    def __init__(self, households: List[Household]):
        self.members = households

    def __iter__(self):
        return iter(self.members)
    
    def __len__(self):
        return len(self.members)

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
