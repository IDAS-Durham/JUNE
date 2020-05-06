from covid.groups import Group
import numpy as np
from itertools import count


class Household(Group):
    """
    The Household class represents a household and contains information about 
    its residents.
    """

    _id = count()

    def __init__(self, composition=None, communal=False, area=None, max_size=np.inf):
        house_id = next(self._id)
        super().__init__(f"Household_{house_id}", "household")
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
