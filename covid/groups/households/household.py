from enum import IntEnum

from covid.groups import Group


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
        kids         = 0
        young_adults = 1
        adults       = 2
        old_adults   = 3

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
                if person.active_group is None:
                    person.active_group = "household"


class Households:
    """
    Contains all households for the given area, and information about them.
    """

    def __init__(self, world):
        self.world = world
        self.members = []
