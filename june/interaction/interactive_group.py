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

    def __init__(self, group: Group, people_from_abroad = None):
        infector_ids = []
        trans_prob = []
        susceptible_ids = []
        infector_subgroup_sizes = []
        self.subgroups_infector = []
        self.subgroups_susceptible = []
        self.has_susceptible = False
        self.has_infector = False
        self.n_foreign_people = 0
        for i, subgroup in enumerate(group.subgroups):
            if (
                people_from_abroad is not None
                and subgroup.subgroup_type in people_from_abroad
            ):
                people_abroad_data = people_from_abroad[subgroup.subgroup_type]
                people_abroad_ids = list(people_abroad_data.keys())
                self.n_foreign_people += len(people_abroad_ids)
                people_abroad_infected_ids = [
                    id
                    for id in people_abroad_ids
                    if people_abroad_data[id]["inf_prob"] > 0
                ]
                people_abroad_susceptible_ids = [
                    id
                    for id in people_abroad_ids
                    if people_abroad_data[id]["susc"] > 0.0
                ]
                people_abroad_infected_prob = [
                    people_abroad_data[id]["inf_prob"]
                    for id in people_abroad_ids
                    if people_abroad_data[id]["inf_prob"] > 0
                ]
                subgroup_size = len(subgroup.people) + len(people_abroad_ids)
                if subgroup_size == 0:
                    continue
                subgroup_infected = [
                    person
                    for person in subgroup
                    if person.infection is not None
                    and person.infection.transmission.probability > 0
                ]
                sus_ids = [
                    person.id for person in subgroup.people if person.susceptible
                ] + people_abroad_susceptible_ids
                if sus_ids:
                    self.has_susceptible = True
                    self.subgroups_susceptible.append(i)
                    susceptible_ids.append(sus_ids)

                inf_ids = [
                    person.id for person in subgroup_infected
                ] + people_abroad_infected_ids
                if inf_ids:
                    tprob = sum(
                        person.infection.transmission.probability
                        for person in subgroup_infected
                    ) + sum(people_abroad_infected_prob)
                    self.has_infector = True
                    self.subgroups_infector.append(i)
                    trans_prob.append(tprob)
                    infector_ids.append(inf_ids)
                    infector_subgroup_sizes.append(subgroup_size)
            else:
                subgroup_size = len(subgroup.people)
                if subgroup_size == 0:
                    continue
                subgroup_infected = [
                    person
                    for person in subgroup
                    if person.infection is not None
                    and person.infection.transmission.probability > 0
                ]
                sus_ids = [
                    person.id for person in subgroup.people if person.susceptible
                ]
                if sus_ids:
                    self.has_susceptible = True
                    self.subgroups_susceptible.append(i)
                    susceptible_ids.append(sus_ids)

                inf_ids = [person.id for person in subgroup_infected]
                if inf_ids:
                    tprob = sum(
                        person.infection.transmission.probability
                        for person in subgroup_infected
                    )
                    self.has_infector = True
                    self.subgroups_infector.append(i)
                    trans_prob.append(tprob)
                    infector_ids.append(inf_ids)
                    infector_subgroup_sizes.append(subgroup_size)

        self.must_timestep = self.has_susceptible and self.has_infector
        self.size = group.size + self.n_foreign_people
        if self.must_timestep is False:
            return
        self.spec = group.spec
        self.infector_ids = infector_ids
        self.transmission_probabilities = trans_prob
        self.susceptible_ids = susceptible_ids
        # self.subgroups_susceptible = self.subgroups_susceptible
        # self.subgroups_infector = self.subgroups_infector
        self.infector_subgroup_sizes = infector_subgroup_sizes
        if self.spec == "school":
            self.school_years = group.years
        else:
            self.school_years = None
