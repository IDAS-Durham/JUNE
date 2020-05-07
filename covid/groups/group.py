import logging
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import List

import numpy as np

from covid.exc import GroupException

logger = logging.getLogger(__name__)


class AbstractGroup(ABC):
    @property
    @abstractmethod
    def people(self):
        pass

    @property
    @abstractmethod
    def susceptible(self) -> List:
        """
        People susceptible to the disease
        """

    @property
    @abstractmethod
    def infected(self) -> List:
        """
        People currently infected with the disease
        """

    @property
    @abstractmethod
    def recovered(self) -> List:
        """
        People recovered from the disease
        """

    @property
    def size(self):
        return len(self.people)

    @property
    def size_susceptible(self):
        return len(self.susceptible)

    @property
    def size_infected(self):
        return len(self.infected)

    @property
    def size_recovered(self):
        return len(self.recovered)

    def __contains__(self, item):
        return item in self.people

    def __iter__(self):
        return iter(self.people)


class People(AbstractGroup):
    def __init__(self, intensity=1.0):
        self._people = set()
        self.intensity = intensity

    @property
    def susceptible(self) -> set:
        """
        People susceptible to the disease
        """
        return {
            person for person in self.people
            if person.health_information.susceptible
        }

    @property
    def infected(self) -> set:
        """
        People currently infected with the disease
        """
        return {
            person for person in self.people
            if person.health_information.infected and not (
                    person.health_information.in_hospital
                    or person.health_information.dead
            )
        }

    @property
    def recovered(self) -> set:
        """
        People recovered from the disease
        """
        return {
            person for person in self.people
            if person.health_information.recovered
        }

    def clear(self):
        self._people = []

    @property
    def people(self):
        return self._people

    def update_status_lists(self, time, delta_time):
        for person in self.people:
            person.health_information.update_health_status(time, delta_time)
            if person.health_information.dead:
                person.bury()
                self._people.remove(person)

    def append(self, person):
        self._people.add(person)

    def remove(self, person):
        self._people.remove(person)

    def __getitem__(self, item):
        return list(self._people)[item]


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

    @property
    def susceptible(self) -> set:
        return self._susceptible

    @property
    def infected(self) -> set:
        return self._infected

    @property
    def recovered(self) -> set:
        return self._recovered

    @property
    def people(self):
        return [
            person for
            grouping in self.groupings
            for person in grouping.people
        ]

    allowed_groups = [
        "area",
        "box",
        "boundary",
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
        default = 0

    def __init__(self, name, spec):
        self.sane(name, spec)
        self.name = name
        self.spec = spec
        self.n_groupings = len(self.GroupType)
        self.groupings = [People() for _ in range(self.n_groupings)]
        self.intensity = np.ones((self.n_groupings, self.n_groupings))
        self._susceptible = set()
        self._infected = set()
        self._recovered = set()
        self.in_hospital = set()
        self.dead = set()

        self.intensity = 1.0

    def remove_person(self, person):
        for grouping in self.groupings:
            if person in grouping:
                grouping.remove(person)

    def sane(self, name, spec):
        if spec not in self.allowed_groups:
            raise GroupException(f"{spec} is not an allowed group type")

    def __getitem__(self, item):
        return self.groupings[item]

    def add(self, person, qualifier=GroupType.default):
        self.groupings[qualifier].append(person)

    def clear(self):
        for grouping in self.groupings:
            grouping.clear()

    def set_active_members(self):
        for grouping in self.groupings:
            for person in grouping.people:
                if person.active_group is not None:
                    raise ValueError("Trying to set an already active person")
                else:
                    person.active_group = self.spec

    @property
    def must_timestep(self):
        return (self.size > 1 and
                self.size_infected > 0 and
                self.size_susceptible > 0)

    def update_status_lists(self, time, delta_time):
        for grouping in self.groupings:
            grouping.update_status_lists(time, delta_time)

        self._susceptible.clear()
        self._infected.clear()
        self._recovered.clear()
        self.in_hospital.clear()
        self.dead.clear()

        for person in self.people:
            health_information = person.health_information
            health_information.update_health_status(time, delta_time)
            if health_information.susceptible:
                self._susceptible.add(person)
            elif health_information.infected_at_home:
                self._infected.add(person)
            elif health_information.in_hospital:
                self.in_hospital.add(person)
            elif health_information.recovered:
                self._recovered.add(person)
            elif person.health_information.dead:
                self.dead.add(person)
                
    @property 
    def intensities(self):
        return np.eye(len(self.groupings), len(self.groupings))

    @property
    def size(self):
        return len(self.people)

    @property
    def size_susceptible(self):
        return len(self.susceptible)

    @property
    def size_infected(self):
        return len(self.infected)

    @property
    def size_recovered(self):
        return len(self.recovered)


def symmetrize_matrix(matrix):
    return (matrix + matrix.T) / 2


def reciprocal_matrix(matrix, demography):
    demography_matrix = demography.reshape(-1, 1) / demography.reshape(1, -1)
    return (matrix + matrix.T * demography_matrix) / 2


class TestGroups():
    def __init__(self, N):
        self.members = []
        self.members.append([])
        self.members[0].append(Group("Test", "Random", 1000))
        print(self)
