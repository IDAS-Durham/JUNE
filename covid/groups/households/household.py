from covid.groups import Group
import numpy as np


class Household(Group):
    """
    The Household class represents a household and contains information about 
    its residents.
    """

    def __init__(self, house_id=None, composition=None, communal=False, area=None, max_size=np.inf):
        if house_id is None:
            super().__init__(None, "household") 
        else:
            super().__init__("Household_%03d"%house_id, "household") 
        self.id = house_id
        self.area = area
        self.household_composition = composition
        self.communal = communal
        self.max_size = max_size

    def set_active_members(self):
        for person in self.people:
            if person.active_group is None:
                person.active_group = "household"

class Households:
    """
    Contains all households for the given area, and information about them.
    """

    def __init__(self, world):
        self.world = world
        self.members = []
