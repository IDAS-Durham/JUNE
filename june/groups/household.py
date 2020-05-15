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

    __slots__ = (
        "area",
        "communal",
        "max_size",
        "must_supervise_age",
        "stay_at_home_complacency",
    )

    class GroupType(IntEnum):
        kids = 0
        young_adults = 1
        adults = 2
        old_adults = 3

    def __init__(self, communal=False, area=None, max_size=np.inf):
        super().__init__()
        self.area = area
        self.communal = communal
        self.max_size = max_size

    def add(self, person, subgroup_type=GroupType.adults):
        for mate in self.people:
            if person != mate:
                person.housemates.append(mate)
        super().add(
            person, group_type=person.GroupType.residence, subgroup_type=subgroup_type
        )

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
