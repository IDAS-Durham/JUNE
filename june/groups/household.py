from enum import IntEnum


import numpy as np
import random
import h5py
import time

from june.groups.group import Group, Supergroup
from enum import IntEnum
from typing import List

nan_integer = -999


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
        Erases all people from subgroups.
        Erases all subgroup references to group.
        Empties housemates list.
        """
        for group in self:
            for person in group.people:
                person.housemates.clear()
            for subgroup in group.subgroups:
                subgroup._people.clear()
                subgroup.group = None

    def to_hdf5(self, file_path: str):
        n_households = len(self.members)
        ids = []
        areas = []
        communals = []
        max_sizes = []
        for household in self.members:
            ids.append(household.id)
            if household.area is None:
                areas.append(nan_integer)
            else:
                areas.append(household.area.id)
            communals.append(household.communal)
            max_sizes.append(household.max_size)
        ids = np.array(ids, dtype=np.int)
        areas = np.array(areas, dtype=np.int)
        communals = np.array(communals, dtype=np.bool)
        max_sizes = np.array(max_sizes, dtype=np.float)
        with h5py.File(file_path, "w") as f:
            people_dset = f.create_group("households")
            people_dset.attrs["n_households"] = n_households
            people_dset.create_dataset("id", data=ids)
            people_dset.create_dataset("area", data=areas)
            people_dset.create_dataset("communal", data=communals)
            people_dset.create_dataset("max_size", data=max_sizes)

    @classmethod
    def from_hdf5(cls, file_path: str):
        with h5py.File(file_path, "r") as f:
            households = f["households"]
            households_list = list()
            chunk_size = 50000
            n_households = households.attrs["n_households"]
            n_chunks = int(np.ceil(n_households / chunk_size))
            for chunk in range(n_chunks):
                idx1 = chunk * chunk_size
                idx2 = min((chunk + 1) * chunk_size, n_households)
                ids = households["id"][idx1:idx2]
                communals = households["communal"][idx1:idx2]
                areas = households["area"][idx1:idx2]
                max_sizes = households["max_size"][idx1:idx2]
                for k in range(idx2 - idx1):
                    area = areas[k]
                    if area == nan_integer:
                        area = None
                    household = Household(
                        communal=communals[k], area=area, max_size=max_sizes[k]
                    )
                    household.id = ids[k]
                    households_list.append(household)
        return cls(households_list)
