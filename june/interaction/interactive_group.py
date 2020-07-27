import numpy as np
import numba as nb

from june.groups import Group


class InteractiveGroup:
    """
    Extracts the necessary information about a group to perform an interaction time
    step over it. This step is necessary, since all the information is stored in numpy
    arrays that allow for efficient computation.

    Parameters
    ----------
    - group : group that we want to prepare for interaction.
    """

    def __init__(self, group: Group):
        infector_ids = []
        trans_prob = []
        susceptible_ids = []
        infector_subgroup_sizes = []
        self.subgroups_infector = []
        self.subgroups_susceptible = []
        self.has_susceptible = False
        self.has_infector = False
        self.size = group.size
        for i, subgroup in enumerate(group.subgroups):
            subgroup_size = len(subgroup.people)
            subgroup_infected = [
                person
                for person in subgroup
                if person.health_information is not None
                and person.health_information.infection.transmission.probability > 0
            ]
            sus_ids = [person.id for person in subgroup.people if person.susceptible]
            if len(sus_ids) != 0:
                self.has_susceptible = True
                self.subgroups_susceptible.append(i)
                susceptible_ids.append(np.array(sus_ids))

            inf_ids = [person.id for person in subgroup_infected]
            if len(inf_ids) != 0:
                tprob = sum(
                    person.health_information.infection.transmission.probability
                    for person in subgroup_infected
                )
                self.has_infector = True
                self.subgroups_infector.append(i)
                trans_prob.append(tprob)
                infector_ids.append(np.array(inf_ids))
                infector_subgroup_sizes.append(subgroup_size)

        self.must_timestep = self.has_susceptible and self.has_infector
        if self.must_timestep is False:
            return
        self.spec = group.spec
        self.infector_ids = tuple(infector_ids)
        self.transmission_probabilities = tuple(trans_prob)
        self.susceptible_ids = tuple(susceptible_ids)
        self.subgroups_susceptible = tuple(self.subgroups_susceptible)
        self.subgroups_infector = tuple(self.subgroups_infector)
        self.infector_subgroup_sizes = tuple(infector_subgroup_sizes)
        if self.spec == "school":
            self.school_years = group.years
        else:
            self.school_years = None


if __name__ == "__main__":
    import time
    from june.groups import Household
    from june.demography import Person
    from june.infection import InfectionSelector

    selector = InfectionSelector.from_file()
    household = Household()
    i = 0
    for i in range(0, 10):
        p = Person.from_attributes()
        household.add(p, subgroup_type=i % len(household.subgroups))
        if i % 2 == 0:
            selector.infect_person_at_time(p, 0)
            p.health_information.update_health_status(5, 5)
    # household.clear()
    t1 = time.time()
    for _ in range(300_000):
        interactive_group = InteractiveGroup(household)
    t2 = time.time()
    print(f"took {t2-t1} seconds")
