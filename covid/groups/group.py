import logging
from typing import List

import matplotlib.pyplot as plt

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
        "box",
        "boundary"
        "commute_Public",
        "commute_Private",
        "company",
        "household",
        "hospital",
        "leisure_Outdoor",
        "leisure_Indoor",
        "random",
        "referenceGroup",
        "shopping",
        "school",
        "testGroup",
        "work_Outdoor",
        "work_Indoor",
    ]

    def __init__(self, name, spec, number=-1):
        if not self.sane(name, spec):
            return
        self.name = name
        self.spec = spec
        self.people = []
        self.intensity = 1.0

    @property
    def susceptible(self) -> List:
        """
        People in this group who are susceptible to the disease
        """
        return [
            person for person in self.people
            if person.health_information.susceptible
        ]

    @property
    def infected(self) -> List:
        """
        People in this group who are currently infected with the disease
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
        People in this group who have recovered from the disease
        """
        return [
            person for person in self.people
            if person.health_information.recovered
        ]

    def sane(self, name, spec):
        if not spec in self.allowed_groups:
            print("Error: tried to initialise group with wrong specification:", spec)
            return False
        return True

    def set_active_members(self):
        for person in self.people:
            if person.active_group is not None:
                raise ValueError("Trying to set an already active person")
            else:
                person.active_group = self.spec

    def update_status_lists(self):
        logger.debug("=== update status list for group with ", len(self.people), " people ===")
        for person in self.people:
            person.health_information.update_health_status()
            if person.health_information.infected:
                if person.health_information.must_stay_at_home:
                    continue
                    # print ("person must stay at home",person.id,":",
                    #       person.health_information.tag," for",
                    #       person.health_information.infection.symptoms.severity)
                    # don't add this person to the group
                    # the household group instance deals with this in its own
                    # update_status_lists method
                elif person.health_information.in_hospital:
                    logger.debug("person should be in hospital", person.id, ":",
                                 person.health_information.tag, " for",
                                 person.health_information.infection.symptoms.severity)
                    person.get_into_hospital()
                    self.people.remove(person)
                    continue

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
