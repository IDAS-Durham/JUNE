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

    __slots__ = "area", "household_composition", "communal", "max_size"

    class GroupType(IntEnum):
        kids = 0
        young_adults = 1
        adults = 2
        old_adults = 3

    def __init__(self, composition=None, communal=False, area=None, max_size=np.inf):
        super().__init__()
        self.area = area
        self.household_composition = composition
        self.communal = communal
        self.max_size = max_size
        self.must_supervise_age = 14 
        self.stay_at_home_complacency = 0.95

    def add(self, person, qualifier=GroupType.adults, subgroup_type_qualifier=GroupType.adults):
        super().add(person, qualifier, subgroup_type_qualifier)
        person.household = self

    def select_random_parent(self):
        parents = [
            person
            for person in self.people
            if person not in list(self.subgroups[self.GroupType.kids].people) and
            not person.health_information.in_hospital
        ]
        #TODO what happens if there are no parents ?? 
        if parents:
            return random.choice(parents)
        else:
            return None

    def set_active_members(self):
        for person in self.people:
            if person.health_information.must_stay_at_home and person.age <= self.must_supervise_age:
                person.active_group = person.subgroups[person.GroupType.residence] 
                random_parent = self.select_random_parent()
                if random_parent is not None:
                    print('Home alone :)')
                    random_parent.active_group = random_parent.subgroups[random_parent.GroupType.residence]
            elif person.health_information.must_stay_at_home and person.active_group is not None:
                if random.random() <= self.stay_at_home_complacency:
                    person.active_group = person.subgroups[person.GroupType.residence] 
            elif person.active_group is None:
                if person.health_information.dead:
                    continue
                person.active_group = person.subgroups[person.GroupType.residence]
    
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
