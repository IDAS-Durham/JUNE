import numpy as np
from random import randint, random
import yaml
from typing import List, Tuple
from june.interaction.interaction import Interaction


def random_choice(people):
    idx = randint(0, len(people) - 1)
    return people[idx]


class ContactSampling(Interaction):
    def __init__(self, betas, contact_matrices, selector):
        self.betas = betas
        self.contact_matrices = contact_matrices
        self.selector = selector

    def number_of_contacts(
        self,
        subgroup_i: "Subgroup",
        subgroup_j: "Subgroup",
        group_spec: str,
        delta_time: float,
    ) -> int:
        """
        Get the number of contacts between one member of subgroup i, with members of subgroup j,
        using the contact matrix to sample from a Poisson distribution.

        Parameters
        ----------
        subgroup_i:
            first subgroup interacting with,
        subgroup_j:
            second subgroup
        group_spec:
            specifier of the group, to access the contact matrix
        delta_time:
            time over which to run the interaction
        Returns
        -------
            number of contacts
        """
        idx_i = subgroup_i.subgroup_type
        idx_j = subgroup_j.subgroup_type
        n_contacts_per_day = self.contact_matrices.get(group_spec)[idx_i][idx_j]
        #TODO: betas should enter here
        n_contacts = np.random.poisson(n_contacts_per_day * delta_time)
        return n_contacts

    def sample_susceptible_pairs_for_infected(
        self, infecter: "Person", subgroup_j: "Subgroup", n_contacts: int
    ) -> List["Person"]:
        """
        Sample the susceptible people that the infected individual contacts

        Parameters
        ----------
        infecter:
            infected person looking for people to infect
        subgroup_j:
            subgroup of people looking to be infected 
        n_contacts:
            number of contacts the infecter has with people from subgroup_j
        Returns
        -------
            list of susceptible people to contact
        """
        if infecter in subgroup_j.people:
            susceptibles = np.random.choice(
                [person for person in subgroup_j.people if person != infecter],
                size=n_contacts,
            )
        else:
            susceptibles = np.random.choice(subgroup_j.people, size=n_contacts)
        return [person for person in susceptibles if person.susceptible]

    def sample_pair(
        self, subgroup_i: "Subgroup", subgroup_j: "Subgroup", 
    ) -> Tuple["Person"]:
        """
        Sample the susceptible people that the infected individual contacts

        Parameters
        ----------
        subgroup_j:
            subgroup of people looking to be infected 
        n_contacts:
            number of contacts the infecter has with people from subgroup_j
        Returns
        -------
            list of susceptible people to contact
        """
        person_i = random_choice(subgroup_i.people)
        if subgroup_i == subgroup_j:
            person_j = random_choice([person for person in subgroup_j if person != person_i])
        else:
            person_j = random_choice(subgroup_j.people)

        return (person_i, person_j) 

    def pair_interaction(
        self,
        infecter: "Person",
        susceptibles: List["Person"],
        group_spec: str,
        time: float,
    ):
        """
        Make the infecter interact with all susceptibles
        
        Parameters
        ----------
        infecter:
            infected person looking for people to infect
        susceptibles:
            list of susceptible people
        group_spec:
            specifier of the group, to read contact matrices and intensity information
        time:
            time at which the infection might happen
        """
        should_be_infected = random(len(susceptibles))
        # TODO: should add susceptibility somewhere here if needed
        for recipient, luck in zip(susceptibles, should_be_infected):
            if luck < infecter.health_information.infection.transmission.probability:
                self.selector.infect_person_at_time(person=recipient, time=time)
                recipient.health_information.update_infection_data(
                    time=time, group_type=group_spec, infecter=None, logger=None
                )

    def single_time_step_for_group(
        self, group: "Group", time: float, delta_time: float, logger: "Logger"
    ):
        """
        Run the interaction for a time step over the group.

        Parameters
        ----------
        group:
            group over which we run the interaction
        time:
            time at which the interaction happens (in units of days)
        delta_time:
            duration of the interaction (in units of days)
        logger:
            logger to save R related information 
        """
        group_spec = group.spec
        for i, subgroup_i in enumerate(group.subgroups):
            for subgroup_j in group.subgroups[i:]:
                n_contacts = self.number_of_contacts(
                    subgroup_i, subgroup_j, group_spec, delta_time
                )
                for n in range(n_contacts):
                    pair = self.sample_pairs(subgroup_i, subgroup_j)
                    self.pair_interaction(pair, group_spec, time)
