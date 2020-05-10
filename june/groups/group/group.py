import logging
from enum import IntEnum
from typing import Set

from june.exc import GroupException
from june.demography.person import Person
from .abstract import AbstractGroup
from .subgroup import Subgroup

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

    allowed_groups = [
        "area",
        "box",
        "boundary",
        "carehome",
        "commute_Public",
        "commute_Private",
        "cemetery",
        "company",
        "household",
        "hospital",
        "leisure_Outdoor",
        "leisure_Indoor",
        "pub",
        "random",
        "TestGroup",
        "referenceGroup",
        "shopping",
        "school",
        "super_area",
        "testGroup",
        "work_Outdoor",
        "work_Indoor",
    ]

    class GroupType(IntEnum):
        """
        Defines the indices of subgroups within the subgroups array
        """
        default = 0

    __slots__ = "name", "spec", "subgroups"

    def __init__(self, name: str, spec: str):
        """
        A group of people such as in a hospital or a school.

        Parameters
        ----------
        name
            The name of this particular instance.
        spec
            The kind of group this is
        """
        if spec not in self.allowed_groups:
            raise GroupException(f"{spec} is not an allowed group type")

        self.name = name
        self.spec = spec
        # noinspection PyTypeChecker
        self.subgroups = [
            Subgroup()
            for _
            in range(len(
                self.GroupType
            ))
        ]

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

    def __getitem__(self, item: GroupType) -> "Subgroup":
        """
        A subgroup with a given index
        """
        return self.subgroups[item]

    def add(
            self,
            person: Person,
            qualifier=GroupType.default
    ):
        """
        Add a person to a given subgroup. For example, in a school
        a student is added to the subgroup matching their age.

        Parameters
        ----------
        person
            A person
        qualifier
            An enumerated so the student can be added to a given group
        """
        self[qualifier].append(person)
        person.groups.append(self)

    def set_active_members(self):
        for person in self.people:
            if person.active_group is None:
                person.active_group = self.spec

    @property
    def people(self) -> Set[Person]:
        """
        All the people in this group
        """
        return self._collate_from_subgroups(
            "people"
        )

    def _collate_from_subgroups(
            self,
            attribute: str
    ) -> Set[Person]:
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
        collection = set()
        for grouping in self.subgroups:
            collection.update(
                getattr(grouping, attribute)
            )
        return collection

    @property
    def susceptible(self):
        return self._collate_from_subgroups(
            "susceptible"
        )

    @property
    def infected(self):
        return self._collate_from_subgroups(
            "infected"
        )

    @property
    def recovered(self):
        return self._collate_from_subgroups(
            "recovered"
        )

    @property
    def in_hospital(self):
        return self._collate_from_subgroups(
            "in_hospital"
        )

    @property
    def dead(self):
        return self._collate_from_subgroups(
            "dead"
        )

    @property
    def must_timestep(self):
        return (self.size > 1 and
                self.size_infected > 0 and
                self.size_susceptible > 0)

    @property
    def size_active(self):
        n_active = 0
        for person in self.people:
            if person.active_group == self.spec:
                n_active += 1
        return n_active


