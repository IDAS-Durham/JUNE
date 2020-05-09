from enum import IntEnum
import random
import numpy as np

from covid.groups import Group


must_stay_at_home_complacency = 0.98
must_supervise_age = 14


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

    class GroupType(IntEnum):
        kids = 0
        young_adults = 1
        adults = 2
        old_adults = 3

    def __init__(self, house_id, composition, area):
        super().__init__("Household_%03d" % house_id, "household")
        self.id = house_id
        self.area = area
        self.household_composition = composition

    def add(self, person, qualifier=GroupType.adults):
        super().add(person, qualifier)
        person.household = self
        person.groups.append(self)

    def set_active_members(self):
        for grouping in self.groupings:
            for person in grouping.people:
                if person.health_information.dead:
                    continue
                elif person.active_group is None:
                    person.active_group = "household"
                elif person.health_information.must_stay_at_home:
                    if person.age <= must_supervise_age:
                        person.active_group = "household"
                        # randomly pick a parent to stay with the kid
                        random_parent.active_group = "household"
                    else:
                        if random.random() <= must_stay_at_home_complacency:
                            person.active_group = "household"
                        else:
                            continue


class Households:
    """
    Contains all households for the given area, and information about them.
    """

    def __init__(self, world):
        self.world = world
        self.members = []
