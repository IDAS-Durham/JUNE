import numpy as np
import yaml
import numba as nb
from numpy.random import choice
from random import random
from typing import List, Dict
from itertools import chain
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from june.demography import Population

from june.exc import InteractionError
from june.utils import parse_age_probabilities
from june.groups.group.interactive import InteractiveGroup
from june.groups import InteractiveSchool, InteractiveCompany, InteractiveHousehold
from june.records import Record
from june import paths

default_config_filename = paths.configs_path / "defaults/interaction/interaction.yaml"

default_sector_beta_filename = (
    paths.configs_path / "defaults/interaction/sector_beta.yaml"
)


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
        betas: Dict[str, float],
        contact_matrices: dict,
        susceptibilities_by_age: Dict[str, int] = None,
        population: "Population" = None,
    ):
        self.alpha_physical = alpha_physical
        self.betas = betas or {}
        contact_matrices = contact_matrices or {}
        self.contact_matrices = self.process_contact_matrices(
            input_contact_matrices=contact_matrices,
            groups=self.betas.keys(),
            alpha_physical=alpha_physical,
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
        # This dict is to keep track of beta reductions introduced by policies:
        self.beta_reductions = {}

    @classmethod
    def from_file(
        cls,
        config_filename: str = default_config_filename,
        population: "Population" = None,
    ) -> "Interaction":
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        contact_matrices = config["contact_matrices"]
        if "susceptibilities" in config:
            susceptibilities_by_age = config["susceptibilities"]
        else:
            susceptibilities_by_age = None
        return Interaction(
            alpha_physical=config["alpha_physical"],
            betas=config["betas"],
            contact_matrices=contact_matrices,
            susceptibilities_by_age=susceptibilities_by_age,
            population=population,
        )

    def set_population_susceptibilities(
        self, susceptibilities_by_age: dict, population: "Population"
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

    def process_contact_matrices(
        self, groups: List[str], input_contact_matrices: dict, alpha_physical: float
    ):
        """
        Processes the input data regarding to contacts to construct the contact matrix used in the interaction.
        In particular, given a contact matrix, a matrix of physical contact ratios, and the physical contact weighting
        (alpha_physical) constructs the contact matrix via:
        $ contact_matrix = contact_matrix * (1 + (alpha_physical - 1) * physical_ratios) $

        Parameters
        ----------
        groups
            a list of group names that will be handled by the interaction
        input_contact_data
            configuration regarding contact matrices and physical contacts
        alpha_physical
            The relative weight of physical conctacts respect o non-physical ones.
        """
        contact_matrices = {}
        for group in groups:
            # school is a special case.
            contact_data = input_contact_matrices.get(group, {})
            contact_matrix = np.array(contact_data.get("contacts", [[1]]))
            proportion_physical = np.array(
                contact_data.get("proportion_physical", [[0]])
            )
            characteristic_time = contact_data.get("characteristic_time", 8)
            if group == "school":
                contact_matrix = InteractiveSchool.get_processed_contact_matrix(
                    contact_matrix=contact_matrix,
                    proportion_physical=proportion_physical,
                    alpha_physical=alpha_physical,
                    characteristic_time=characteristic_time,
                )
            else:
                contact_matrix = InteractiveGroup.get_processed_contact_matrix(
                    contact_matrix=contact_matrix,
                    proportion_physical=proportion_physical,
                    alpha_physical=alpha_physical,
                    characteristic_time=characteristic_time,
                )
            contact_matrices[group] = contact_matrix
        return contact_matrices

    def _get_interactive_group_beta(self, interactive_group):
        return interactive_group.get_processed_beta(
            betas=self.betas, beta_reductions=self.beta_reductions
        )

    def time_step_for_group(
        self,
        group: "Group",
        delta_time: float,
        people_from_abroad: dict = None,
        record: Record = None,
    ):
        """
        Runs an interaction time step for the given interactive group. First, we
        give the beta and contact matrix to the group to process it. There may be groups
        that change the betas depending on the situation, ie, a school interactive group,
        has to treat the contact matrix on a special way, or the company beta may change
        due to the company's sector. Second, we iterate over all subgroups that contain
        susceptible people, and compute the interaction between them and the subgroups that
        contain infected people.

        Parameters
        ----------
        group:
            An instance of InteractiveGroup
        delta_time:
            Time interval of the interaction
        """
        interactive_group = group.get_interactive_group(
            people_from_abroad=people_from_abroad
        )
        if not interactive_group.must_timestep:
            return [], [], interactive_group.size
        infected_ids = []
        infection_ids = []
        to_blame_ids = []
        beta = self._get_interactive_group_beta(interactive_group)
        contact_matrix = self.contact_matrices[group.spec]
        for susceptible_subgroup_index, susceptible_subgroup_global_index in enumerate(
            interactive_group.subgroups_with_susceptible
        ):
            # the susceptible_subgroup_index tracks the particular subgroup
            # inside the list of susceptible subgroups.
            # the susceptible_subgroup_global_index tracks the particular
            # subgroup inside the list of all subgroups
            (
                new_infected_ids,
                new_to_blame_ids,
                new_infection_ids,
            ) = self._time_step_for_subgroup(
                susceptible_subgroup_index=susceptible_subgroup_index,
                susceptible_subgroup_global_index=susceptible_subgroup_global_index,
                interactive_group=interactive_group,
                beta=beta,
                contact_matrix=contact_matrix,
                delta_time=delta_time,
            )
            infected_ids += new_infected_ids
            to_blame_ids += new_to_blame_ids
            infection_ids += new_infection_ids
        if record:
            self._log_infections_to_record(
                infected_ids=infected_ids,
                infection_ids=infection_ids,
                to_blame_ids=to_blame_ids,
                record=record,
                group=group,
            )
        return infected_ids, infection_ids, interactive_group.size

    def _time_step_for_subgroup(
        self,
        susceptible_subgroup_index: int,
        susceptible_subgroup_global_index: int,
        interactive_group: InteractiveGroup,
        beta: float,
        contact_matrix: float,
        delta_time: float,
    ) -> List[int]:
        """
        Time step for one susceptible subgroup. We first compute the combined
        effective transmission probability of all the subgroups that contain infected
        people, and then run this effective transmission over the susceptible subgroup,
        to check who got infected.

        Parameters
        ----------
        susceptible_subgroup_index:
            index of the susceptible subgroup that is interacting with the infected subgroups.
        group
            The InteractiveGroup of the time step.
        beta
            Interaction intensity for this particular interactive group
        contact matrix
            contact matrix of this interactive group
        delta_time
            time interval
        """
        (
            effective_transmission_exponent,
            infector_weights,
            infector_ids,
            infector_infection_ids,
        ) = self._compute_effective_transmission_exponent(
            susceptible_subgroup_global_index=susceptible_subgroup_global_index,
            interactive_group=interactive_group,
            beta=beta,
            contact_matrix=contact_matrix,
            delta_time=delta_time,
        )
        subgroup_infected_ids = self._sample_new_infected_people(
            effective_transmission_exponent=effective_transmission_exponent,
            subgroup_susceptible_ids=interactive_group.susceptible_ids[
                susceptible_subgroup_index
            ],
            subgroup_suscetibilities=interactive_group.susceptible_susceptibilities[
                susceptible_subgroup_index
            ],
        )
        to_blame_ids, to_blame_infection_ids = self._assign_blame_for_infections(
            n_infections=len(subgroup_infected_ids),
            infector_weights=infector_weights,
            infector_ids=infector_ids,
            infector_infection_ids=infector_infection_ids,
        )
        return subgroup_infected_ids, to_blame_ids, to_blame_infection_ids

    def _compute_effective_transmission_exponent(
        self,
        susceptible_subgroup_global_index: int,
        interactive_group: InteractiveGroup,
        beta: float,
        contact_matrix: np.array,
        delta_time: float,
    ):
        """
        Computes the effective transmission probability of all the infected people in the group,
        that is, the sum of all infection probabilities divided by the number of infected people.

        Parameters
        ----------
        - subgroup_transmission_probabilities : transmission probabilities per subgroup.
        - susceptibles_group_idx : indices of suceptible people
        - subgroups_with_infector_sizes: subgroup sizes where the infected people are.
        - contact_matrix : contact matrix of the group
        """
        transmission_exponent = 0.0
        infector_weights = []
        infector_ids = []
        infector_infection_ids = []
        for infector_subgroup_index, infector_subgroup_global_index in enumerate(
            interactive_group.subgroups_with_infectors
        ):
            infector_subgroup_size = interactive_group.subgroups_with_infectors_sizes[
                infector_subgroup_index
            ]
            # same logic in this loop as in the previous susceptible subgroups loop
            if infector_subgroup_global_index == susceptible_subgroup_global_index:
                # subgroup interacting with itself, must discount the own person.
                infector_subgroup_size -= 1
                if infector_subgroup_size == 0:
                    continue
            n_contacts_between_subgroups = (
                interactive_group.get_contacts_between_subgroups(
                    contact_matrix=contact_matrix,
                    subgroup_1_idx=susceptible_subgroup_global_index,
                    subgroup_2_idx=infector_subgroup_global_index,
                )
            )
            infector_ids += interactive_group.infector_ids[infector_subgroup_index]
            infector_infection_ids += interactive_group.infector_infection_ids[
                infector_subgroup_index
            ]
            subgroup_transmission_exponent_list = [
                infector_transmission_probability
                * n_contacts_between_subgroups
                / infector_subgroup_size
                for infector_transmission_probability in interactive_group.infector_transmission_probabilities[
                    infector_subgroup_index
                ]
            ]
            infector_weights += subgroup_transmission_exponent_list
            transmission_exponent += sum(subgroup_transmission_exponent_list)
        print(transmission_exponent)
        return (
            transmission_exponent * delta_time * beta,
            infector_weights,
            infector_ids,
            infector_infection_ids,
        )

    def _sample_new_infected_people(
        self,
        effective_transmission_exponent,
        subgroup_susceptible_ids,
        subgroup_suscetibilities,
    ):
        """
        Samples for new infections in the interaction of a susceptible subgroup with all the infector subgroups.

        Parameters
        ----------
        effective_transmission_exponent
            Part of the exponent of the transmission probability. The complete formula is
            Ptrans = 1 - np.exp(- effective_transmission_exponent * susceptibility)
        susceptible_ids
            list of ids of susceptible people to check for new infections
        suscetibilities
            susceptibilities of the susceptible people
        """
        infected_ids = []
        for susceptible_id, susceptibility in zip(
            subgroup_susceptible_ids, subgroup_suscetibilities
        ):
            transmission_probability = 1.0 - np.exp(
                -effective_transmission_exponent * susceptibility
            )
            if random() < transmission_probability:
                infected_ids.append(susceptible_id)
        return infected_ids

    def _assign_blame_for_infections(
        self, n_infections, infector_weights, infector_ids, infector_infection_ids
    ):
        """
        Given a number of infections, ```n_infections```, assigns blame to
        infectors based on their relative contribution to the overall
        transmission probability.

        Parameters
        ----------
        n_infections
            Number of infections that have been produced
        infector_weights
            weights of each infector in the transmission prob.
        infector_ids
            ids of the infectors
        """
        if n_infections == 0:
            return [], []
        infector_weights = np.array(infector_weights)
        sel_idcs = list(
            choice(
                np.arange(0, len(infector_ids)),
                size=n_infections,
                p=infector_weights / infector_weights.sum(),
            )
        )
        to_blame_ids = []
        to_blame_infection_ids = []
        for idx in sel_idcs:
            to_blame_ids.append(infector_ids[idx])
            to_blame_infection_ids.append(infector_infection_ids[idx])
        return to_blame_ids, to_blame_infection_ids

    def _log_infections_to_record(
        self,
        infected_ids: list,
        infection_ids: list,
        to_blame_ids: list,
        group: "Group",
        record: Record,
    ):
        """
        Logs new infected people to record, and their infectors.
        """
        record.accumulate(
            table_name="infections",
            location_spec=group.spec,
            location_id=group.id,
            region_name=group.super_area.region.name,
            infected_ids=infected_ids,
            infection_ids=infection_ids,
            infector_ids=to_blame_ids,
        )
