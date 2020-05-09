from itertools import count

import numpy as np
import random

from june.groups.group import Group
from enum import IntEnum


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
        self.must_supervise_age = 14
        self.stay_at_home_complacency = 0.95

    def add(self, person, qualifier=GroupType.adults):
        super().add(person, qualifier)
        person.household = self

    def select_random_parent(self)
        parents = [
            person
            for person in self.people
            if person
            not in list(self.groupings[self.GroupType.kids].people)
        ]

        return random.choice(parents)

    def set_active_members(self):
        for grouping in self.subgroups:
            for person in grouping.people:
                if person.health_information.dead:
                    continue
                elif person.active_group is None:
                    person.active_group = 'household'
                elif person.health_information.must_stay_at_home:
                    if person.age <= self.must_supervise_age:
                        person.active_group = 'household'
                        random_parent = self.select_random_parent()
                        random_parent.active_group = 'household'
                    else:
                        if random.random() <= self.stay_at_home_complacency:
                            person.active_group = 'household'

class Households:
    """
    Contains all households for the given area, and information about them.
    """

    def __init__(self):
        self.members = []

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
