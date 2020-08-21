import numpy as np
import yaml
import numba as nb
from random import random
from typing import List
from june import paths
from june.interaction.interactive_group import InteractiveGroup
from itertools import chain

default_config_filename = (
    paths.configs_path / "defaults/interaction/ContactInteraction.yaml"
)


@nb.jit(nopython=True)
def get_contact_matrix(alpha, contacts, physical):
    """
    Computes the contact matrix used in the interaction,
    which boosts the physical contacts by a factor.

    Parameters
    ----------
    - alpha : relative weight of physical contacts respect to the normal ones.
    (1 = same as normal).
    - contacts : contact matrix
    - physical : proportion of physical contacts.
    """
    return contacts * (1.0 + (alpha - 1.0) * physical)


# @nb.jit(nopython=True)
def compute_effective_transmission(
    subgroup_transmission_probabilities: np.array,
    susceptibles_group_idx: np.array,
    infector_subgroups: tuple,
    infector_subgroup_sizes: np.array,
    contact_matrix: np.array,
    delta_time: float,
    beta: float,
    school_years: np.array,
):
    """
    Computes the effective transmission probability of all the infected people in the group,
    that is, the sum of all infection probabilities divided by the number of infected people.

    Parameters
    ----------
    - subgroup_transmission_probabilities : transmission probabilities per subgroup.
    - susceptibles_group_idx : indices of suceptible people
    - infector_subgroup_sizes : subgroup sizes where the infected people are.
    - contact_matrix : contact matrix of the group
    """
    transmission_exponent = 0.0
    for i in range(len(infector_subgroup_sizes)):
        subgroup_trans_prob = subgroup_transmission_probabilities[i]
        subgroup_size = infector_subgroup_sizes[i]
        transmission_exponent += _subgroup_to_subgroup_transmission(
            contact_matrix=contact_matrix,
            subgroup_transmission_probabilities=subgroup_trans_prob,
            subgroup_size=subgroup_size,
            susceptibles_idx=susceptibles_group_idx,
            infecters_idx=infector_subgroups[i],
            school_years=school_years,
        )
    poisson_exponent = transmission_exponent * delta_time * beta
    return 1.0 - np.exp(-poisson_exponent)


# @nb.jit(nopython=True)
def infect_susceptibles(effective_transmission_probability, susceptible_ids):
    infected_ids = []
    for id in susceptible_ids:
        if random() < effective_transmission_probability:
            infected_ids.append(id)
    return infected_ids


@nb.jit(nopython=True)
def _get_contacts_in_school(
    contact_matrix, school_years, susceptibles_idx, infecters_idx
):
    n_contacts = contact_matrix[
        _translate_school_subgroup(susceptibles_idx, school_years)
    ][_translate_school_subgroup(infecters_idx, school_years)]
    if susceptibles_idx == 0 and infecters_idx > 0:
        n_contacts /= len(school_years)
    if (
        _translate_school_subgroup(susceptibles_idx, school_years)
        == _translate_school_subgroup(infecters_idx, school_years)
        and susceptibles_idx != infecters_idx
    ):
        # If same age but different class room, no contacts
        n_contacts = 0
    return n_contacts


# @nb.jit(nopython=True)
def _subgroup_to_subgroup_transmission(
    contact_matrix,
    subgroup_transmission_probabilities,
    subgroup_size,
    susceptibles_idx,
    infecters_idx,
    school_years=None,
) -> float:
    if school_years is not None:
        n_contacts = _get_contacts_in_school(
            contact_matrix, school_years, susceptibles_idx, infecters_idx
        )
    else:
        n_contacts = contact_matrix[susceptibles_idx][infecters_idx]
    if susceptibles_idx == infecters_idx:
        subgroup_size -= 1
        if subgroup_size == 0:
            return 0.0
    return n_contacts / subgroup_size * subgroup_transmission_probabilities


@nb.jit(nopython=True)
def _translate_school_subgroup(idx, school_years):
    if idx > 0:
        idx = school_years[idx - 1] + 1
    return idx


class Interaction:
    def __init__(self, alpha_physical, beta, contact_matrices):
        self.alpha_physical = alpha_physical
        self.beta = beta
        self.contact_matrices = self.process_contact_matrices(
            groups=beta.keys(), input_contact_matrices=contact_matrices
        )

    @classmethod
    def from_file(
        cls, config_filename: str = default_config_filename
    ) -> "ContactAveraging":
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        contact_matrices = config["contact_matrices"]
        return Interaction(
            alpha_physical=config["alpha_physical"],
            beta=config["beta"],
            contact_matrices=contact_matrices,
        )

    def process_contact_matrices(self, groups: List[str], input_contact_matrices: dict):
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

    def time_step_for_group(self, delta_time: float, group: InteractiveGroup):
        contact_matrix = self.contact_matrices[group.spec]
        beta = self.beta[group.spec]
        school_years = group.school_years
        infected_ids = []
        if len(group.subgroups_susceptible) == 1:
            infected_ids = self.time_step_for_subgroup(
                contact_matrix=contact_matrix,
                subgroup_transmission_probabilities=group.transmission_probabilities,
                susceptible_ids=group.susceptible_ids[0],
                infector_subgroups=group.subgroups_infector,
                infector_subgroup_sizes=group.infector_subgroup_sizes,
                beta=beta,
                delta_time=delta_time,
                subgroup_idx=group.subgroups_susceptible[0],
                school_years=school_years,
            )
        else:
            for i, subgroup_id in enumerate(group.subgroups_susceptible):
                susceptible_ids = group.susceptible_ids[i]
                infected_ids += self.time_step_for_subgroup(
                    contact_matrix=contact_matrix,
                    subgroup_transmission_probabilities=group.transmission_probabilities,
                    susceptible_ids=susceptible_ids,
                    infector_subgroups=group.subgroups_infector,
                    infector_subgroup_sizes=group.infector_subgroup_sizes,
                    beta=beta,
                    delta_time=delta_time,
                    subgroup_idx=subgroup_id,
                    school_years=school_years,
                )
        return infected_ids

    def time_step_for_subgroup(
        self,
        subgroup_transmission_probabilities,
        susceptible_ids,
        infector_subgroups,
        infector_subgroup_sizes,
        contact_matrix,
        beta,
        delta_time,
        subgroup_idx,
        school_years,
    ) -> List[int]:
        effective_transmission_probability = compute_effective_transmission(
            subgroup_transmission_probabilities=subgroup_transmission_probabilities,
            susceptibles_group_idx=subgroup_idx,
            infector_subgroups=infector_subgroups,
            infector_subgroup_sizes=infector_subgroup_sizes,
            contact_matrix=contact_matrix,
            beta=beta,
            delta_time=delta_time,
            school_years=school_years,
        )
        infected_ids = infect_susceptibles(
            effective_transmission_probability, susceptible_ids
        )
        return infected_ids
