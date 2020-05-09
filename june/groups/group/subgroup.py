from june.demography.person import Person
from .abstract import AbstractGroup
from typing import Set


class Subgroup(AbstractGroup):
    __slots__ = "_people", "_susceptible", "_infected", "_recovered", "_in_hospital", "_dead"

    def __init__(self):
        """
        A group within a group. For example, children in a household.
        """
        self._people = set()
        self._susceptible = set()
        self._infected = set()
        self._recovered = set()
        self._in_hospital = set()
        self._dead = set()

    def _collate(
            self,
            attribute: str
        ) -> Set[Person]:
        collection = set()
        for person in self.people:
            if getattr(person.health_information, attribute):
                collection.add(
                    person
                    )
        return collection

    def _collate_active(
            self, 
            set_of_people,
            active_group
            ):
        collection = set()
        for person in set_of_people:
            if person.active_group == active_group:
                collection.add(
                    person
                    )
        return collection


    @property
    def susceptible(self):
        return self._collate('susceptible')

    def susceptible_active(self, active_group):
        return self._collate_active(self.susceptible, active_group)

    @property
    def infected(self):
        return self._collate('infected')

    def infected_active(self, active_group):
        return self._collate_active(self.infected, active_group)

    @property
    def recovered(self):
        return self._collate('recovered')

    def infected_recovered(self, active_group):
        return self._collate_active(self.recovered, active_group)


    @property
    def in_hospital(self):
        return self._in_hospital

    @property
    def dead(self):
        return self._dead

    def __contains__(self, item):
        return item in self._people

    def __iter__(self):
        return iter(self._people)

    def clear(self):
        self._people = set()

    @property
    def people(self):
        return self._people

    def append(self, person: Person):
        """
        Add a person to this group
        """
        self._people.add(person)

    def remove(self, person: Person):
        """
        Remove a person from this group
        """
        self._people.remove(person)

    def __getitem__(self, item):
        return list(self._people)[item]
