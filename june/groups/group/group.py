import logging
import re
import numpy as np
from collections import defaultdict
from enum import IntEnum
from itertools import count
from typing import List, Tuple

from june.demography.person import Person
from june.exc import GroupException
from .interactive import InteractiveGroup
from . import AbstractGroup
from . import Subgroup

logger = logging.getLogger(__name__)


class Group(AbstractGroup):
    """
    A group of people enjoying social interactions.  It contains three lists,
    all people in the group, the healthy ones and the infected ones (we may
    have to add the immune ones as well).

    This is very basic and we will have to specify derived classes with
    additional information - like household, work, commute - where some,
    like household groups are stable and others, like commute groups, are
    randomly assorted on a step-by-step base.

    The logic is that the group will enjoy one Interaction per time step,
    where the infection spreads, with a probablity driven by transmission
    probabilities and inteaction intensity, plus, possilby, individual
    susceptibility to become infected.

    TODO: we will have to decide in how far specific groups define behavioral
    patterns, which may be time-dependent.  So, far I have made a first pass at
    a list of group specifiers - we could promote it to a dicitonary with
    default intensities (maybe mean+width with a pre-described range?).
    """

    external = False

    class SubgroupType(IntEnum):
        """
        Defines the indices of subgroups within the subgroups array
        """

        default = 0

    __slots__ = ("id", "subgroups", "spec")

    __id_generators = defaultdict(count)

    @classmethod
    def _next_id(cls) -> int:
        """
        Iterate an id for this class. Each group class has its own id iterator
        starting at 0
        """
        return next(cls.__id_generators[cls])

    def __init__(self):
        """
        A group of people such as in a hospital or a school.

        If a spec attribute is not defined in the child class then it is generated
        by converting the class name into snakecase.
        """
        self.id = self._next_id()
        self.spec = self.get_spec()
        # noinspection PyTypeChecker
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
        except:
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

    def __getitem__(self, item: SubgroupType) -> "Subgroup":
        """
        A subgroup with a given index
        """
        return self.subgroups[item]

    def add(
        self,
        person: Person,
        activity: str,
        subgroup_type: SubgroupType,  # , dynamic=False
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
