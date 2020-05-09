from june.demography.person import Person
from .abstract import AbstractGroup


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

    @property
    def susceptible(self):
        return self._susceptible

    @property
    def infected(self):
        return self._infected

    @property
    def recovered(self):
        return self._recovered

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
