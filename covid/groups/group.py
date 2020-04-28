import matplotlib.pyplot as plt
from covid import exc

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
    where the infection spreads, with a probability driven by transmission
    probabilities and inteaction intensity, plus, possilbly, individual
    susceptibility to become infected.

    TODO: we will have to decide in how far specific groups define behavioral
    patterns, which may be time-dependent.  So, far I have made a first pass at
    a list of group specifiers - we could promote it to a dicitonary with
    default intensities (maybe mean+width with a pre-described range?).
    """

    allowed_groups = [
        "household",
        "school",
        "company",
        "hospital",
        "work_Outdoor",
        "work_Indoor",
        "commute_Public",
        "commute_Private",
        "leisure_Outdoor",
        "leisure_Indoor",
        "shopping",
        "referenceGroup",
        "random",
        "testGroup",
        "box"
    ]

    
    def __init__(self, name, spec, number=-1):

        if spec not in self.allowed_groups:
            raise exc.GroupException("Tried to initialise group with an invalid specification:", spec)

        self.name = name
        self.spec = spec
        self._intensity = 1.0
        self.people = []
        self.susceptible = []
        self.infected = []
        self.recovered = []
        if self.spec == "Random":
            self.fill_random_group(number)

    def set_active_members(self):
        for person in self.people:
            if person.active_group is not None:
                raise ValueError("Trying to set an already active person")
            else:
                person.active_group = self.spec

    @property
    def intensity(self):
        return self._intensity

    @intensity.setter
    def intensity(self, intensity):
        self._intensity = intensity

    def update_status_lists(self, time=1):
        print ("=== update status list for group with ",len(self.people)," people ===")
        self.susceptible.clear()
        self.infected.clear()
        self.recovered.clear()
        for person in self.people:
            person.health_information.update_health_status()
            if person.health_information.susceptible:
                self.susceptible.append(person)
            if person.health_information.infected:
                if person.health_information.must_stay_at_home:
                    continue
                    #print ("person must stay at home",person.id,":",
                    #       person.health_information.tag," for",
                    #       person.health_information.infection.symptoms.severity)
                    # don't add this person to the group
                    # the household group instance deals with this in its own
                    # update_status_lists method
                elif person.health_information.in_hospital:
                    print ("person should be in hospital",person.id,":",
                           person.health_information.tag," for",
                           person.health_information.infection.symptoms.severity)
                    person.get_into_hospital()
                    self.people.remove(person)
                    continue
                    # don't add this person to the group
                    # the hospital group instance deals with this in its own
                    # update_status_lists method
                elif person.health_information.dead:
                    continue
                    # never add dead people
                else:
                    self.infected.append(person)
            elif person.health_information.recovered:
                self.recovered.append(person)
                if person in self.infected:
                    self.infected.remove(person)

    def clear(self, all=True):
        if all:
            self.people.clear()
        self.susceptible.clear()
        self.infected.clear()
        self.recovered.clear()

    def output(self, plot=False, full=False,time = 0):
        print("==================================================")
        print("Group ",self.name,", type = ",self.spec," with ",len(self.people)," people.")
        print("* ",
            self.size_susceptible(),"(",round(len(self.susceptible) / len(self.people) * 100),"%) are susceptible, ",
            self.size_infected(),   "(",round(len(self.infected) / len(self.people) * 100),   "%) are infected,",
            self.size_recovered(),  "(",round(len(self.recovered) / len(self.people) * 100),  "%) have recovered.",
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
              F,"(",round(F / len(self.people) * 100.0),"%) females, ",
              M,"(",round(M / len(self.people) * 100.0),"%) males;",
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
    def __init__(self,N):
        self.members = []
        self.members.append([])
        self.members[0].append(Group("Test","Random",1000))
        print (self)
