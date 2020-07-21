import numpy as np
import yaml
import numba as nb
from typing import List
from june import paths
from june.interaction.interaction import Interaction

default_config_filename = (
    paths.configs_path / "defaults/interaction/ContactInteraction.yaml"
)


@nb.jit(nopython=True)
def poisson_probability(delta_time, susceptibilities, beta, transmission_exponent):
    return 1.0 - np.exp(-delta_time * susceptibilities * beta * transmission_exponent)


@nb.jit(nopython=True)
def get_contact_matrix(alpha, contacts, physical):
    return contacts * (1.0 + (alpha - 1.0) * physical)


class ContactAveraging(Interaction):
    def __init__(
        self, alpha_physical, beta, contact_matrices, selector, inverted=False
    ):
        self.alpha_physical = alpha_physical
        self.beta = beta
        self.contact_matrices = self.process_contact_matrices(
            groups=beta.keys(), input_contact_matrices=contact_matrices
        )
        self.selector = selector
        self.inverted = inverted

    @classmethod
    def from_file(
        cls, config_filename: str = default_config_filename, selector=None,
    ) -> "ContactAveraging":
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        contact_matrices = config["contact_matrices"]
        return ContactAveraging(
            alpha_physical=config["alpha_physical"],
            beta=config["beta"],
            contact_matrices=contact_matrices,
            selector=selector,
        )

    def process_contact_matrices(self, groups, input_contact_matrices):
        contact_matrices = {}
        default_contacts = np.array([[1]])
        default_characteristic_time = 8
        default_proportion_physical = np.array([[0]])
        for group in groups:
            if group not in input_contact_matrices.keys():
                contacts = default_contacts
                proportion_physical = default_proportion_physical
                characteristic_time = default_characteristic_time
            else:
                if group == "school":
                    (
                        contacts,
                        proportion_physical,
                        characteristic_time,
                    ) = self.process_school_matrices(input_contact_matrices[group])
                else:
                    contacts = np.array(input_contact_matrices[group]["contacts"])
                    proportion_physical = np.array(
                        input_contact_matrices[group]["proportion_physical"]
                    )
                    characteristic_time = input_contact_matrices[group][
                        "characteristic_time"
                    ]
            contact_matrices[group] = get_contact_matrix(
                self.alpha_physical, contacts, proportion_physical,
            )
            contact_matrices[group] *= 24 / characteristic_time
        return contact_matrices

    def process_school_matrices(self, input_contact_matrices, age_min=0, age_max=20):
        contact_matrices = {}
        contact_matrices["contacts"] = self.adapt_contacts_to_schools(
            input_contact_matrices["contacts"],
            input_contact_matrices["xi"],
            age_min=age_min,
            age_max=age_max,
            physical=False,
        )
        contact_matrices["proportion_physical"] = self.adapt_contacts_to_schools(
            input_contact_matrices["proportion_physical"],
            input_contact_matrices["xi"],
            age_min=age_min,
            age_max=age_max,
            physical=True,
        )
        return (
            contact_matrices["contacts"],
            contact_matrices["proportion_physical"],
            input_contact_matrices["characteristic_time"],
        )

    def adapt_contacts_to_schools(
        self, input_contact_matrix, xi, age_min, age_max, physical=False
    ):
        n_subgroups_max = (age_max - age_min) + 2  # adding teachers
        contact_matrix = np.zeros((n_subgroups_max, n_subgroups_max))
        contact_matrix[0, 0] = input_contact_matrix[0][0]
        contact_matrix[0, 1:] = input_contact_matrix[0][1]
        contact_matrix[1:, 0] = input_contact_matrix[1][0]
        age_differences = np.subtract.outer(
            range(age_min, age_max + 1), range(age_min, age_max + 1)
        )
        if physical:
            contact_matrix[1:, 1:] = input_contact_matrix[1][1]
        else:
            contact_matrix[1:, 1:] = (
                xi ** abs(age_differences) * input_contact_matrix[1][1]
            )
        return contact_matrix

    def get_sum_transmission_per_subgroup(self, group: "Group") -> List[float]:
        """
        Given a group, computes the sum of the transmission probabilities 
        of the infected people per subgroup

        Parameters
        ----------

        group:
            instance of group to run the interaction model on
        """
        return [
            sum(
                [
                    person.health_information.infection.transmission.probability
                    for person in subgroup.infected
                ]
            )
            for subgroup in group.subgroups
        ]

    def assign_blame(self, infected, subgroup_transmission_probabilities):
        norm = sum(subgroup_transmission_probabilities)
        for person in infected:
            person.health_information.number_of_infected += (
                person.health_information.infection.transmission.probability / norm
            )

    def get_contacts_in_school(
        self, contact_matrix, school_years, susceptibles_idx, infecters_idx
    ):
        n_contacts = contact_matrix[
            self.translate_school_subgroup(susceptibles_idx, school_years)
        ][self.translate_school_subgroup(infecters_idx, school_years)]
        # teacher's contacts with students spread out among class rooms
        if susceptibles_idx == 0 and infecters_idx > 0:
            n_contacts /= len(school_years)
        return n_contacts

    def subgroup_to_subgroup_transmission(
        self,
        contact_matrix,
        subgroup_transmission_probabilities,
        susceptibles_subgroup,
        infecters_subgroup,
    ) -> float:
        """
        Computes the transmission power from one subgroup to another, given by their
        number of contacts that a susceptible person might do with an infected person in
        the other subgroup, and the total transmission probability of the other subgroup.

        Parameters
        ----------
        susceptibles_subgroup:
            subgroup containing susceptible people
        infecters_subgroup:
            subgroup containing infected people
        Returns
        -------
            number of contacts a susceptible person has with infected people,
            times the average transmission probability of the subgroup with infected people
        """
        if self.inverted:
            subgroup_size = len(susceptibles_subgroup)
        else:
            subgroup_size = len(infecters_subgroup)
        if susceptibles_subgroup == infecters_subgroup:
            subgroup_size -= 1
        susceptibles_idx = susceptibles_subgroup.subgroup_type
        infecters_idx = infecters_subgroup.subgroup_type
        if susceptibles_subgroup.group.spec == "school":
            n_contacts = self.get_contacts_in_school(
                contact_matrix,
                susceptibles_subgroup.group.years,
                susceptibles_idx,
                infecters_idx,
            )
        elif susceptibles_subgroup.group.spec == "commute":
            # decreasing not peak commute contacts by 20%
            peak_not_peak = np.random.choice(2,1,[0.8,0.2])
            if peak_not_peak == 1:
                n_contacts = contact_matrix[susceptibles_idx][infecters_idx] * 0.8
            else:
                n_contacts = contact_matrix[susceptibles_idx][infecters_idx]
        else:
            n_contacts = contact_matrix[susceptibles_idx][infecters_idx]
        return (
            n_contacts
            / subgroup_size
            * subgroup_transmission_probabilities[infecters_idx]
        )

    def translate_school_subgroup(self, idx, school_years):
        if idx > 0:
            idx = school_years[idx - 1] + 1
        return idx

    # @profile
    def compute_effective_transmission(
        self,
        contact_matrix,
        subgroup_transmission_probabilities,
        susceptibilities: np.array,
        susceptibles_subgroup: "Subgroup",
        group: "Group",
        delta_time: float,
    ) -> List[float]:
        """
        Compute the effective transmission probability of infected people, by summing the 
        transmissions from different subgroups.

        Parameters
        ----------
        susceptibles_subgroup:
            subgroup containing the susceptible people
        group:
            group in which the interaction takes place
        delta_time:
            duration of the interaction

        Returns
        -------
            list of transmission probabilities for each susceptible person
        """
        transmission_exponent = 0.0
        for subgroup in group.subgroups:
            if subgroup.infected:
                transmission_exponent += self.subgroup_to_subgroup_transmission(
                    contact_matrix,
                    subgroup_transmission_probabilities,
                    susceptibles_subgroup,
                    subgroup,
                )
        return poisson_probability(
            delta_time=delta_time,
            susceptibilities=susceptibilities,
            beta=self.beta[group.spec],
            transmission_exponent=transmission_exponent,
        )

    # @profile
    def single_time_step_for_subgroup(
        self,
        contact_matrix,
        subgroup_transmission_probabilities,
        susceptibles_subgroup: "Subgroup",
        group: "Group",
        time: float,
        delta_time: float,
        logger: "Logger",
    ):
        """
        Run the interaction for a time step over a subgroup
        
        Parameters
        ----------
        susceptibles_subgroup: 
            subgroup with susceptible people
        group:
            group containing all subgroups
        time:
            time at which the interaction happens (in units of days)
        delta_time:
            duration of the interaction (in units of days)
        """
        susceptibles = susceptibles_subgroup.susceptible
        susceptibilities = np.array([person.susceptibility for person in susceptibles])
        transmission_probability = self.compute_effective_transmission(
            contact_matrix,
            subgroup_transmission_probabilities,
            susceptibilities,
            susceptibles_subgroup,
            group,
            delta_time,
        )
        should_be_infected = np.random.rand(len(susceptibles))
        for i, (recipient, luck) in enumerate(zip(susceptibles, should_be_infected)):
            if luck < transmission_probability[i]:
                self.selector.infect_person_at_time(person=recipient, time=time)
                try:
                    logger.accumulate_infection_location(group.spec)
                except:
                    pass
                self.assign_blame(group.infected, subgroup_transmission_probabilities)

    def single_time_step_for_group(
        self, group: "Group", time: float, delta_time: float, logger: "Logger",
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
        contact_matrix = self.contact_matrices[group.spec]
        if self.inverted:
            contact_matrix = contact_matrix.T
        subgroup_transmission_probabilities = self.get_sum_transmission_per_subgroup(
            group
        )
        for susceptibles_subgroup in group.subgroups:
            if len(susceptibles_subgroup.susceptible) > 0:
                self.single_time_step_for_subgroup(
                    contact_matrix,
                    subgroup_transmission_probabilities,
                    susceptibles_subgroup,
                    group,
                    time,
                    delta_time,
                    logger,
                )
