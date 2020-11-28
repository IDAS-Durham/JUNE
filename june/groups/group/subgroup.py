from june.demography.person import Person
from .abstract import AbstractGroup
from typing import List
from itertools import chain


class Subgroup(AbstractGroup):
    external = False
    __slots__ = (
        "group",
        "subgroup_type",
        "people",
    )

    def __init__(self, group, subgroup_type: int):
        """
        A group within a group. For example, children in a household.
        """
        self.group = group
        self.subgroup_type = subgroup_type
        self.people = []

    def _collate(self, attribute: str) -> List[Person]:
        return [person for person in self.people if getattr(person, attribute)]

    @property
    def spec(self):
        return self.group.spec

    @property
    def infected(self):
        return self._collate("infected")

    @property
    def susceptible(self):
        return self._collate("susceptible")

    @property
    def recovered(self):
        return self._collate("recovered")

    @property
    def dead(self):
        return self._collate("dead")

    @property
    def dead(self):
        return self._collate("dead")

    @property
    def in_hospital(self):
        return self._collate("in_hospital")

    def __contains__(self, item):
        return item in self.people

    def __iter__(self):
        return iter(self.people)

    def __len__(self):
        return len(self.people)

    def clear(self):
        self.people = []

    @property
    def contains_people(self) -> bool:
        """
        Whether or not the group contains people.
        """
        return len(self.people) > 0

    def append(self, person: Person):
        """
        Add a person to this group
        """
        self.people.append(person)
        person.busy = True

    def remove(self, person: Person):
        self.people.remove(person)
        person.busy = False

    def __getitem__(self, item):
        return list(self.people)[item]
