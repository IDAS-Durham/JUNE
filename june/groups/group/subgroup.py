from june.demography.person import Person
from .abstract import AbstractGroup
from typing import Set


class Subgroup(AbstractGroup):
    __slots__ = "_people", "_susceptible", "_infected", "_recovered", "_in_hospital", "_dead"

    def __init__(self, spec):
        """
        A group within a group. For example, children in a household.
        """
        self.spec = spec
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
            ):
        collection = set()
        for person in set_of_people:
            if person.active_group == self:
                collection.add(
                    person
                    )
        return collection

    @property
    def susceptible(self):
        return self._collate('susceptible')

    def susceptible_active(self):
        return self._collate_active(self.susceptible)

    @property
    def infected(self):
        return self._collate('infected')

    def infected_active(self):
        return self._collate_active(self.infected)

    @property
    def recovered(self):
        return self._collate('recovered')

    def recovered_active(self):
        return self._collate_active(self.recovered)

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

    @property
    def contains_people(self) -> bool:
        """
        Whether or not the group contains people.
        """
        return len(self._people) > 0

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

    def set_active_members(self):
        for person in self.people:
            #TODO: this dead line shouldnt be necessary, if dead the person
            # should have left the group. However, it doesnt seem to happen
            # for children that go to school and die
            if person.active_group is None and not person.health_information.dead:
                person.active_group = self

    def __getitem__(self, item):
        return list(self._people)[item]
