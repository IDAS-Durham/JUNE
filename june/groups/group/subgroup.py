from june.demography.person import Person
from .abstract import AbstractGroup
from typing import Set, List
from itertools import chain


class Subgroup:
    __slots__ = (
        "group",
        "subgroup_type",
        "people",
        "size",
        "size_infected",
        "size_recovered",
        "size_susceptible",
        "infected",
        "susceptible",
        "recovered",
    )

    def __init__(self, group, subgroup_type: int):
        """
        A group within a group. For example, children in a household.
        """
        self.group = group
        self.subgroup_type = subgroup_type
        self.infected = []
        self.susceptible = []
        self.recovered = []
        self.people = []
        self.size_infected = 0
        self.size_recovered = 0
        self.size_susceptible = 0
        self.size = 0

    def _collate(self, attribute: str) -> List[Person]:
        collection = list()
        for person in self.people:
            if getattr(person, attribute):
                collection.append(person)
        return collection

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
        self.recovered = []
        self.size_recovered = 0
        self.susceptible = []
        self.size_susceptible = 0
        self.infected = []
        self.size_infected = 0
        self.people = []
        self.size = 0

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
        if person.infected:
            self.infected.append(person)
            self.size_infected += 1
        elif person.susceptible:
            self.susceptible.append(person)
            self.size_susceptible += 1
        else:
            self.recovered.append(person)
            self.size_recovered += 1
        self.size += 1
        self.people.append(person)
        self.group.size += 1
        person.busy = True

    def remove(self, person: Person):
        if person.infected:
            self.infected.remove(person)
            self.size_infected -= 1
        elif person.susceptible:
            self.susceptible.remove(person)
            self.size_susceptible -= 1
        else:
            self.recovered.remove(person)
            self.size_recovered -= 1
        self.size -= 1
        self.people.remove(person)
        self.group.size -= 1
        person.busy=False

    def __getitem__(self, item):
        return list(self.people)[item]
