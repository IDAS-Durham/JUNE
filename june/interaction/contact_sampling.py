import numpy as np
import random
import yaml
from june.interaction.interaction import Interaction


def random_choice(people):
    n = len(people)
    idx = np.random.randint(0, high=n)
    return people[idx]


class ContactSampling(Interaction):
    def __init__(self, betas, contact_matrices, selector):
        self.betas = betas
        self.contact_matrices = contact_matrices
        self.selector = selector

    def number_of_contacts(self, subgroup_i, subgroup_j, group_spec, delta_time):
        idx_i = subgroup_i.subgroup_type
        idx_j = subgroup_j.subgroup_type
        n_contacts_per_day = self.contact_matrices.get(group_spec)[idx_i][idx_j]
        n_contacts = np.random.poisson(n_contacts_per_day * delta_time)
        return n_contacts

    def sample_pairs_for_infected(self, infected, subgroup_i, subgroup_j, n_contacts):
        if subgroup_j == subgroup_i:
            susceptibles = np.random.choice(
                [person for person in subgroup_i.people if person != infected],
                size=n_contacts,
            )
        else:
            susceptibles = np.random.choice(subgroup_j.people, size=n_contacts)

        return [person for person in susceptibles if person.susceptible]

    def pair_interaction(self, infecter, susceptibles, group_spec, time):
        should_be_infected = np.random.random(len(susceptibles))
        for recipient, luck in zip(susceptibles, should_be_infected):
            if luck < infecter.health_information.infection.transmission.probability:
                self.selector.infect_person_at_time(person=recipient, time=time)
                recipient.health_information.update_infection_data(
                    time=time, group_type=group_spec, infecter=None, logger=None
                )

    def single_time_step_for_group(self, group, time, delta_time, logger):
        group_spec = group.spec
        for subgroup_i in group.subgroups:
            for subgroup_j in group.subgroups:
                n_contacts = self.number_of_contacts(
                    subgroup_i, subgroup_j, group_spec, delta_time
                )
                for infecter in subgroup_i.infected:
                    susceptibles = self.sample_pairs_for_infected(
                        infecter, subgroup_i, subgroup_j, n_contacts
                    )
                    self.pair_interaction(infecter, susceptibles, group_spec, time)
