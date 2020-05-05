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

    @property
    def susceptible(self) -> List:
        """
        People susceptible to the disease
        """
        return [
            person for person in self.people
            if person.health_information.susceptible
        ]

    def __contains__(self, item):
        return item in self.people

    @property
    def infected(self) -> List:
        """
        People currently infected with the disease
        """
        return [
            person for person in self.people
            if person.health_information.infected and not (
                    person.health_information.in_hospital
                    or person.health_information.dead
            )
        ]

    @property
    def recovered(self) -> List:
        """
        People recovered from the disease
        """
        return [
            person for person in self.people
            if person.health_information.recovered
        ]


class People(AbstractGroup):
    def __init__(self, intensity=1.0):
        self._people = []
        self.intensity = intensity

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
        self._people.append(person)

    def remove(self, person):
        self._people.remove(person)

    def __iter__(self):
        return self._people


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
    def people(self):
        return [
            person for
            group in self.groups
            for person in group.people
        ]

    allowed_groups = [
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
        "referenceGroup",
        "shopping",
        "school",
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
        self.groups = [People() for _ in range(self.n_groups)]
        self.intensities = np.ones((self.n_groups, self.n_groups))

    @property
    def n_groups(self):
        # noinspection PyTypeChecker
        return len(self.GroupType)

    def sane(self, name, spec):
        if spec not in self.allowed_groups:
            raise GroupException(f"{spec} is not an allowed group type")

    def __getitem__(self, item):
        return self.groups[item]

    def add(self, person, qualifier=GroupType.default):
        self.groups[qualifier].append(person)

    def clear(self):
        for group in self.groups:
            group.clear()

    def set_active_members(self):
        for group in self.groups:
            for person in group.people:
                if person.active_group is not None:
                    raise ValueError("Trying to set an already active person")
                else:
                    person.active_group = self.spec

    def must_timestep(self):
        return (self.size > 1 and
                self.size_infected > 0 and
                self.size_susceptible > 0)

    def update_status_lists(self, time, delta_time):
        for group in self.groups:
            group.update_status_lists(time, delta_time)

    def output(self, plot=False, full=False, time=0):
        import matplotlib.pyplot as plt

        print("==================================================")
        print("Group ", self.name, ", type = ", self.spec, " with ", len(self.people), " people.")
        print("* ",
              self.size_susceptible, "(", round(self.size_susceptible / self.size * 100), "%) are susceptible, ",
              self.size_infected, "(", round(self.size_infected / self.size * 100), "%) are infected,",
              self.size_recovered, "(", round(self.size_recovered / self.size * 100), "%) have recovered.",
              )

        ages = []
        M = 0
        F = 0
        for p in self.people:
            ages.append(p.get_age())
            if p.get_sex() == 0:
                M += 1
            else:
                F += 1
        print("* ",
              F, "(", round(F / self.size * 100.0), "%) females, ",
              M, "(", round(M / self.size * 100.0), "%) males;",
              )
        if plot:
            fig, axes = plt.subplots()
            axes.hist(ages, 20, range=(0, 100), density=True, facecolor="blue", alpha=0.5)
            plt.show()
        if full:
            for p in self.people:
                p.output(time)


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
