from enum import IntEnum
from collections import defaultdict
import numpy as np
from random import random
import h5py

from june.groups.group import Group, Supergroup

from enum import IntEnum
from typing import List
from recordclass import dataobject


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
        "type",
        "max_size",
        "residents",
        "quarantine_starting_date",
        "households_to_visit",
        "care_homes_to_visit",
        "ids_checked",
    )

    class SubgroupType(IntEnum):
        kids = 0
        young_adults = 1
        adults = 2
        old_adults = 3

    def __init__(self, type=None, area=None, max_size=np.inf):
        """
        Type should be on of ["family", "student", "young_adults", "old", "other", "nokids", "ya_parents", "communal"].
        Relatives is a list of people that are related to the family living in the household
        """
        super().__init__()
        self.area = area
        self.type = type
        self.quarantine_starting_date = None
        self.relatives_in_care_homes = None
        self.relatives_in_households = None
        self.max_size = max_size
        self.residents = ()
        self.households_to_visit = None
        self.care_homes_to_visit = None

    def add(self, person, subgroup_type=SubgroupType.adults, activity="residence"):
        if activity == "leisure":
            if person.age < 18:
                subgroup = self.SubgroupType.kids
            elif person.age <= 35:
                subgroup = self.SubgroupType.young_adults
            elif person.age < 65:
                subgroup = self.SubgroupType.adults
            else:
                subgroup = self.SubgroupType.old_adults
            person.subgroups.leisure = self[subgroup]
            self[subgroup].append(person)
        elif activity == "residence":
            self[subgroup_type].append(person)
            self.residents = tuple((*self.residents, person))
            person.subgroups.residence = self[subgroup_type]
        else:
            raise NotImplementedError(f"Activity {activity} not supported in household")

    def make_household_residents_stay_home(self, to_send_abroad=None):
        """
        Forces the residents to stay home if they are away doing leisure.
        This is used to welcome visitors.
        """
        for mate in self.residents:
            if mate.busy:
                if (
                    mate.leisure is not None
                ):  # this person has already been assigned somewhere
                    if not mate.leisure.external:
                        if mate not in mate.leisure.people:
                            # person active somewhere else, let's not disturb them
                            continue
                        mate.leisure.remove(mate)
                    else:
                        ret = to_send_abroad.delete_person(mate, mate.leisure)
                        if ret:
                            # person active somewhere else, let's not disturb them
                            continue
                    mate.subgroups.leisure = mate.residence
                    mate.residence.append(mate)
            else:
                mate.subgroups.leisure = (
                    mate.residence  # person will be added later in the simulator.
                )

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

    @property
    def coordinates(self):
        return self.area.coordinates

    def n_residents(self):
        return len(self.residents)

    def quarantine(self, time, quarantine_days, household_compliance):
        if self.type == "communal":
            return False
        if self.quarantine_starting_date:
            if (
                self.quarantine_starting_date
                < time
                < self.quarantine_starting_date + quarantine_days
            ):
                return random() < household_compliance
        return False

    @property
    def super_area(self):
        if self.area is None:
            return None
        else:
            return self.area.super_area


class Households(Supergroup):
    """
    Contains all households for the given area, and information about them.
    """

    def __init__(self, households: List[Household]):
        super().__init__(members=households)
