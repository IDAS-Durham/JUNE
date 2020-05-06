import logging

import matplotlib.pyplot as plt

from june.exc import GroupException

logger = logging.getLogger(__name__)


class Group:
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

    def __init__(self, name, spec):
        self.sane(name, spec)
        self.name = name
        self.spec = spec
        self.people = set()

        self.susceptible = set()
        self.infected = set()
        self.recovered = set()
        self.in_hospital = set()
        self.dead = set()

        self.intensity = 1.0

    def sane(self, name, spec):
        if spec not in self.allowed_groups:
            raise GroupException(f"{spec} is not an allowed group type")

    def set_active_members(self):
        for person in self.people:
            if person.in_hospital is not None:
                person.active_group = None
            elif person.active_group is not None:
                raise ValueError("Trying to set an already active person")
            else:
                person.active_group = self.spec

    def set_intensity(self, intensity):
        self.intensity = intensity

    def get_intensity(self, time=0):
        if self.intensity == None:
            return 1.0
        return self.intensity  # .intensity(time)

    @property
    def must_timestep(self):
        return (self.size > 1 and
                self.size_infected > 0 and
                self.size_susceptible > 0)

    def update_status_lists(self, time, delta_time):
        self.susceptible.clear()
        self.infected.clear()
        self.in_hospital.clear()
        self.recovered.clear()
        self.dead.clear()

        for person in self.people:
            health_information = person.health_information
            health_information.update_health_status(time, delta_time)
            if health_information.susceptible:
                self.susceptible.add(person)
            elif health_information.infected_at_home:
                self.infected.add(person)
            elif health_information.in_hospital:
                self.in_hospital.add(person)
            elif health_information.recovered:
                self.recovered.add(person)
            elif person.health_information.dead:
                self.dead.add(person)

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

    def output(self, plot=False, full=False, time=0):
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

    def get_contact_matrix(self):
        inputs = Inputs()
        return symmetrize_matrix(inputs.contact_matrix)

    def get_reciprocal_matrix(self):
        inputs = Inputs()
        demography = np.array([len(pool) for pool in self.age_pool])
        return reciprocal_matrix(inputs.contact_matrix, demography)


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
