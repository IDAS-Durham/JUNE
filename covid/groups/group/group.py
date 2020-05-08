import logging
from enum import IntEnum

from covid.exc import GroupException
from .abstract import AbstractGroup
from .grouping import Grouping

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
        default = 0

    def __init__(self, name, spec):
        if spec not in self.allowed_groups:
            raise GroupException(f"{spec} is not an allowed group type")

        self.name = name
        self.spec = spec
        # noinspection PyTypeChecker
        self.n_groupings = len(self.GroupType)
        self.groupings = [Grouping() for _ in range(self.n_groupings)]

    def remove_person(self, person):
        for grouping in self.groupings:
            if person in grouping:
                grouping.remove(person)

    def __getitem__(self, item):
        return self.groupings[item]

    def add(self, person, qualifier=GroupType.default):
        self.groupings[qualifier].append(person)

    def set_active_members(self):
        for person in self.people:
            if person.active_group is not None:
                raise ValueError("Trying to set an already active person")
            else:
                person.active_group = self.spec

    @property
    def people(self):
        return [
            person for
            grouping in self.groupings
            for person in grouping.people
        ]

    @property
    def susceptible(self):
        susceptible = set()
        for grouping in self.groupings:
            susceptible.update(
                grouping.susceptible
            )
        return susceptible

    @property
    def infected(self):
        infected = set()
        for grouping in self.groupings:
            infected.update(
                grouping.infected
            )
        return infected

    @property
    def recovered(self):
        recovered = set()
        for grouping in self.groupings:
            recovered.update(
                grouping.recovered
            )
        return recovered

    @property
    def in_hospital(self):
        in_hospital = set()
        for grouping in self.groupings:
            in_hospital.update(
                grouping.in_hospital
            )
        return in_hospital

    @property
    def dead(self):
        dead = set()
        for grouping in self.groupings:
            dead.update(
                grouping.dead
            )
        return dead

    @property
    def must_timestep(self):
        return (self.size > 1 and
                self.size_infected > 0 and
                self.size_susceptible > 0)

    def update_status_lists(self, time, delta_time):
        for grouping in self.groupings:
            grouping.update_status_lists(
                time, delta_time
            )
