import logging
import re
import numpy as np
from collections import defaultdict
from enum import IntEnum
from itertools import count
from typing import List, Optional, Tuple

from june.global_context import GlobalContext
from june.demography.person import Person
from .interactive import InteractiveGroup
from . import AbstractGroup
from . import Subgroup

from june.groups.group.make_subgroups import SubgroupParams

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from june.geography.geography import Region

logger = logging.getLogger(__name__)


class Group(AbstractGroup):
    """
    A group of people enjoying social interactions. It contains three lists:
    all people in the group, the healthy ones, and the infected ones.
    """

    external = False

    __slots__ = ("id", "subgroups", "spec", "subgroup_params")

    __id_generators = defaultdict(count)

    @classmethod
    def _next_id(cls) -> int:
        """
        Iterate an ID for this class. Each group class has its own ID iterator
        starting at 0.
        """
        return next(cls.__id_generators[cls])

    def __init__(self):
        """
        A group of people such as in a hospital or a school.
        """
        # Fetch disease_config from GlobalContext
        disease_config = GlobalContext.get_disease_config()

        self.id = self._next_id()
        self.spec = self.get_spec()

        # Initialize subgroup_params using DiseaseConfig
        self.subgroup_params = SubgroupParams.from_disease_config(disease_config)

        # Define SubgroupType using subgroup_params
        self.SubgroupType = IntEnum(
            "SubgroupType", self.subgroup_params.subgroup_labels(self.spec), start=0
        )

        # Initialize subgroups
        self.subgroups = [Subgroup(self, i) for i in range(len(self.SubgroupType))]

    @property
    def name(self) -> str:
        """
        The name is computed on the fly to reduce memory footprint. It combines
        the name fo the class with the id of the instance.
        """
        return f"{self.__class__.__name__}_{self.id:05d}"

    @property
    def region(self) -> "Region":
        try:
            return self.super_area.region
        except Exception:
            return None

    def get_spec(self) -> str:
        """
        Returns the speciailization of the group.
        """
        return re.sub(r"(?<!^)(?=[A-Z])", "_", self.__class__.__name__).lower()

    def remove_person(self, person: Person):
        """
        Remove a person from this group by removing them
        from the subgroup to which they belong

        Parameters
        ----------
        person
            A person
        """
        for grouping in self.subgroups:
            if person in grouping:
                grouping.remove(person)

    def __getitem__(self, item) -> "Subgroup":
        """
        A subgroup with a given index
        """
        return self.subgroups[item]

    def add(
        self, person: Person, activity: str, subgroup_type: None  # , dynamic=False
    ):
        """
        Add a person to a given subgroup. For example, in a school
        a student is added to the subgroup matching their age.

        Parameters
        ----------
        person
            A person
        group_type

        """
        # if not dynamic:
        if subgroup_type is None:
            subgroup_type = self.get_leisure_subgroup(person)

        self[subgroup_type].append(person)
        if activity is not None:
            setattr(person.subgroups, activity, self[subgroup_type])

    @property
    def people(self) -> Tuple[Person]:
        """
        All the people in this group
        """
        return tuple(
            person for subgroup in self.subgroups for person in subgroup.people
        )

    @property
    def contains_people(self) -> bool:
        """
        Does this group contain at least one person?
        """

        for grouping in self.subgroups:
            if grouping.contains_people:
                return True

        return False

    def _collate_from_subgroups(self, attribute: str) -> List[Person]:
        """
        Return a set of all of the people in the subgroups with a particular health status

        Parameters
        ----------
        attribute
            The name of the attribute in the subgroup, e.g. "in_hospital"

        Returns
        -------
        The union of all the sets with the given attribute name in all of the sub groups.
        """
        return [
            person
            for subgroup in self.subgroups
            for person in subgroup.people
            if getattr(person, attribute)
        ]

    @property
    def susceptible(self):
        return self._collate_from_subgroups("susceptible")

    @property
    def infected(self):
        return self._collate_from_subgroups("infected")

    @property
    def recovered(self):
        return self._collate_from_subgroups("recovered")

    @property
    def in_hospital(self):
        return self._collate_from_subgroups("in_hospital")

    @property
    def dead(self):
        return self._collate_from_subgroups("dead")

    @property
    def must_timestep(self):
        return self.size > 1 and self.size_infected > 0 and self.size_susceptible > 0

    @property
    def size_infected(self):
        return np.sum([subgroup.size_infected for subgroup in self.subgroups])

    @property
    def size_recovered(self):
        return np.sum([subgroup.size_recovered for subgroup in self.subgroups])

    @property
    def size_susceptible(self):
        return np.sum([subgroup.size_susceptible for subgroup in self.subgroups])

    def clear(self):
        for subgroup in self.subgroups:
            subgroup.clear()

    def get_interactive_group(self, people_from_abroad=None):
        return InteractiveGroup(self, people_from_abroad=people_from_abroad)

    def get_leisure_subgroup(self, person, subgroup_type=None, to_send_abroad=None):
        
        if self.subgroup_type == "Age":
            
            min_age = self.subgroup_bins[0]
            max_age = self.subgroup_bins[-1] - 1

            if person.age >= min_age and person.age <= max_age:
                subgroup_idx = (
                    np.searchsorted(self.subgroup_bins, person.age, side="right") - 1
                )
                return self.subgroups[subgroup_idx]
            else:
                return
        elif self.subgroup_type == "Discrete":
            if len(self.subgroups) == 1:
                return self.subgroups[0]
            else:
                return

    def get_index_subgroup(self, person, subgroup_type=None, to_send_abroad=None):
        if self.subgroup_type == "Age":
            min_age = self.subgroup_bins[0]
            max_age = self.subgroup_bins[-1] - 1

            if person.age >= min_age and person.age <= max_age:
                subgroup_idx = (
                    np.searchsorted(self.subgroup_bins, person.age, side="right") - 1
                )
                return subgroup_idx
            else:
                return
        elif self.subgroup_type == "Discrete":
            if len(self.subgroups) == 1:
                return 0
            else:
                return

    @property
    def subgroup_type(self):
        return self.subgroup_params.subgroup_type(self.get_spec())

    @property
    def subgroup_labels(self):
        return self.subgroup_params.subgroup_labels(self.get_spec())

    @property
    def subgroup_bins(self):
        return self.subgroup_params.subgroup_bins(self.get_spec())

    @property
    def kids(self):
        return [
            person
            for subgroup in self.subgroups
            for person in subgroup.people
            if person.age < self.subgroup_params.AgeYoungAdult
        ]

    # @property
    # def young_adults(self):
    #     return [
    #         person
    #         for subgroup in self.subgroups
    #         for person in subgroup.people
    #         if person.age >= self.subgroup_params.AgeYoungAdult and person.age < self.subgroup_params.AgeAdult
    #     ]

    @property
    def adults(self):
        return [
            person
            for subgroup in self.subgroups
            for person in subgroup.people
            if person.age >= self.subgroup_params.AgeAdult
        ]

    # @property
    # def old_adults(self):
    #     return [
    #         person
    #         for subgroup in self.subgroups
    #         for person in subgroup.people
    #         if person.age >= self.subgroup_params.AgeOldAdult
    #     ]

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
        

