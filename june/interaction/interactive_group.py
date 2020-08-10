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
        self.must_timestep = False
        for i, subgroup in enumerate(group.subgroups):
            subgroup_size = len(subgroup.people)
            subgroup_infected = [
                person
                for person in subgroup
                if person.health_information is not None
                and person.health_information.infection.transmission.probability > 0
            ]
            sus_ids = [person.id for person in subgroup.people if person.susceptible]
            inf_ids = [person.id for person in subgroup_infected]

            if sus_ids and inf_ids:
                self.must_timestep = True
                self.subgroups_susceptible.append(i)
                susceptible_ids.append(sus_ids)

                tprob = sum(
                    person.health_information.infection.transmission.probability
                    for person in subgroup_infected
                )
                self.subgroups_infector.append(i)
                trans_prob.append(tprob)
                infector_ids.append(inf_ids)
                infector_subgroup_sizes.append(subgroup_size)

        if self.must_timestep is False:
            return
        self.spec = group.spec
        self.infector_ids = infector_ids
        self.transmission_probabilities = trans_prob
        self.susceptible_ids = susceptible_ids
        #self.subgroups_susceptible = self.subgroups_susceptible
        #self.subgroups_infector = self.subgroups_infector
        self.infector_subgroup_sizes = infector_subgroup_sizes
        if self.spec == "school":
            self.school_years = group.years
        else:
            self.school_years = None
