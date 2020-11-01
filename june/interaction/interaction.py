import numpy as np
import yaml
import numba as nb
from random import random
from typing import List, Dict
from itertools import chain

from june.interaction.interactive_group import InteractiveGroup
from june.demography import Population
from june.exc import InteractionError
from june.utils import parse_age_probabilities
from june import paths

default_config_filename = paths.configs_path / "defaults/interaction/interaction.yaml"

default_sector_beta_filename = paths.configs_path / "defaults/interaction/sector_beta.yaml"


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
    return transmission_exponent * delta_time * beta


# @nb.jit(nopython=True)
def infect_susceptibles(effective_transmission, susceptible_ids, suscetibilities):
    infected_ids = []
    for id, susceptibility in zip(susceptible_ids, suscetibilities):
        transmission_probability = 1.0 - np.exp(
            -effective_transmission * susceptibility
        )
        if random() < transmission_probability:
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
    """
    Class to handle interaction in groups.

    Parameters
    ----------
    alpha_physical
        Scaling factor for physical contacts, an alpha_physical factor of 1, means that physical
        contacts count as much as non-physical contacts.
    beta
        dictionary mapping the group specs with their contact intensities
    contact_matrices
        dictionary mapping the group specs with their contact matrices
    susceptibilities_by_age
        dictionary mapping age ranges to their susceptibility.
        Example: susceptibilities_by_age = {"0-13" : 0.5, "13-99" : 0.5}
        note that the right limit of the range is not included.
    population
        list of people to have the susceptibilities changed.
    """

    def __init__(
        self,
        alpha_physical: float,
        beta: Dict[str, float],
        contact_matrices: dict,
        susceptibilities_by_age: Dict[str, int] = None,
        population: Population = None,
        sector_betas = None,
    ):
        self.alpha_physical = alpha_physical
        self.beta = beta or {}
        contact_matrices = contact_matrices or {}
        self.contact_matrices = self.process_contact_matrices(
            groups=self.beta.keys(), input_contact_matrices=contact_matrices
        )
        self.susceptibilities_by_age = susceptibilities_by_age
        if self.susceptibilities_by_age is not None:
            if population is None:
                raise InteractionError(
                    f"Need to pass population to change susceptibilities by age."
                )
            self.set_population_susceptibilities(
                susceptibilities_by_age=susceptibilities_by_age, population=population
            )
        self.sector_betas = sector_betas

    @classmethod
    def from_file(
        cls,
        config_filename: str = default_config_filename,
        population: Population = None,
        sector_beta = False,
        sector_beta_filename: str = default_sector_filename
    ) -> "Interaction":
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        contact_matrices = config["contact_matrices"]
        if "susceptibilities" in config:
            susceptibilities_by_age = config["susceptibilities"]
        else:
            susceptibilities_by_age = None
        if sector_beta:
            with open(sector_beta_filename) as f:
                sector_beta_config = yaml.load(f, Loader=yaml.FullLoader)
            sector_betas = sector_beta_config["sector_betas"]
        else:
            sector_betas = None
        return Interaction(
            alpha_physical=config["alpha_physical"],
            beta=config["beta"],
            contact_matrices=contact_matrices,
            susceptibilities_by_age=susceptibilities_by_age,
            population=population,
            sector_betas=sector_betas
        )

    def set_population_susceptibilities(
        self, susceptibilities_by_age: dict, population: Population
    ):
        """
        Changes the population susceptibility to the disease.
        """
        susceptibilities_array = parse_age_probabilities(susceptibilities_by_age)
        for person in population:
            if person.age >= len(susceptibilities_array):
                person.susceptibility = susceptibilities_array[-1]
            else:
                person.susceptibility = susceptibilities_array[person.age]

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
        if group.spec == "company" and self.sector_betas is not None:
            beta = self.beta[group.spec]*float(self.sector_betas[group.sector])
        else:
            beta = self.beta[group.spec]
        school_years = group.school_years
        infected_ids = []
        for i, subgroup_id in enumerate(group.subgroups_susceptible):
            susceptible_ids = group.susceptible_ids[i]
            susceptibilities = group.susceptibilities[i]
            infected_ids += self.time_step_for_subgroup(
                contact_matrix=contact_matrix,
                subgroup_transmission_probabilities=group.transmission_probabilities,
                susceptible_ids=susceptible_ids,
                susceptibilities=susceptibilities,
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
        susceptibilities,
        infector_subgroups,
        infector_subgroup_sizes,
        contact_matrix,
        beta,
        delta_time,
        subgroup_idx,
        school_years,
    ) -> List[int]:
        effective_transmission = compute_effective_transmission(
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
            effective_transmission=effective_transmission,
            susceptible_ids=susceptible_ids,
            suscetibilities=susceptibilities,
        )
        return infected_ids
