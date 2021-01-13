from enum import IntEnum
from collections import defaultdict
import numpy as np
from random import random
import h5py

from june.groups import Group, Supergroup, ExternalSubgroup, ExternalGroup
from june.groups.group.interactive import InteractiveGroup

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
        "residences_to_visit",
        "being_visited",
        "household_to_care",
        "receiving_care"
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
        self.quarantine_starting_date = -99
        self.max_size = max_size
        self.residents = ()
        self.residences_to_visit = defaultdict(tuple)
        self.household_to_care = None
        self.being_visited = False  # this is True when people from other households have been added to the group
        self.receiving_care = False

    def _get_leisure_subgroup_for_person(self, person):
        if person.age < 18:
            subgroup = self.SubgroupType.kids
        elif person.age <= 35:
            subgroup = self.SubgroupType.young_adults
        elif person.age < 65:
            subgroup = self.SubgroupType.adults
        else:
            subgroup = self.SubgroupType.old_adults
        return subgroup

    def add(self, person, subgroup_type=SubgroupType.adults, activity="residence"):
        if activity == "leisure":
            subgroup_type = self.get_leisure_subgroup_type(person)
            person.subgroups.leisure = self[subgroup_type]
            self[subgroup_type].append(person)
            self.being_visited = True
        elif activity == "residence":
            self[subgroup_type].append(person)
            self.residents = tuple((*self.residents, person))
            person.subgroups.residence = self[subgroup_type]
        else:
            raise NotImplementedError(f"Activity {activity} not supported in household")

    @classmethod
    def get_leisure_subgroup_type(cls, person):
        """
        A person wants to come and visit this household. We need to assign the person
        to the relevant age subgroup, and make sure the residents welcome him and
        don't go do any other leisure activities.
        """
        if person.age < 18:
            return cls.SubgroupType.kids
        elif person.age <= 35:
            return cls.SubgroupType.young_adults
        elif person.age < 65:
            return cls.SubgroupType.adults
        else:
            return cls.SubgroupType.old_adults

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

    @property
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
        try:
            return self.area.super_area
        except AttributeError:
            return None

    def clear(self):
        super().clear()
        self.being_visited = False
        self.receiving_care = False

    def get_interactive_group(self, people_from_abroad=None):
        return InteractiveHousehold(self, people_from_abroad=people_from_abroad)

    def get_leisure_subgroup(self, person, subgroup_type, to_send_abroad):
        self.being_visited = True
        self.make_household_residents_stay_home(to_send_abroad=to_send_abroad)
        return self[self._get_leisure_subgroup_for_person(person=person)]


class Households(Supergroup):
    """
    Contains all households for the given area, and information about them.
    """

    def __init__(self, households: List[Household]):
        super().__init__(members=households)


class InteractiveHousehold(InteractiveGroup):
    def get_processed_beta(self, betas, beta_reductions):
        """
        In the case of households, we need to apply the beta reduction of household visits
        if the household has a visit, otherwise we apply the beta reduction for a normal 
        household.
        """
        if self.group.receiving_care:
            # important than this goes first than being visited
            beta = betas["care_visits"]
            beta_reduction = beta_reductions.get("care_visits", 1.0)
        elif self.group.being_visited:
            beta = betas["household_visits"]
            beta_reduction = beta_reductions.get("household_visits", 1.0)
        else:
            beta = betas["household"]
            beta_reduction = beta_reductions.get(self.spec, 1.0)
        regional_compliance = self.super_area.region.regional_compliance
        return beta * (1 + regional_compliance * (beta_reduction - 1))

