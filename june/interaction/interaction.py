import numpy as np
import yaml
import numba as nb
from numpy.random import choice
from random import random
from typing import List, Dict
from itertools import chain
from typing import TYPE_CHECKING

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
    """

    def __init__(
        self,
        alpha_physical: float,
        betas: Dict[str, float],
        contact_matrices: dict,
    ):
        self.alpha_physical = alpha_physical
        self.betas = betas or {}
        contact_matrices = contact_matrices or {}
        self.contact_matrices = self.get_raw_contact_matrices(
            input_contact_matrices=contact_matrices,
            groups=self.betas.keys(),
            alpha_physical=alpha_physical,
        )
        self.beta_reductions = {}

    @classmethod
    def from_file(
        cls,
        config_filename: str = default_config_filename,
    ) -> "Interaction":
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        contact_matrices = config["contact_matrices"]
        return Interaction(
            alpha_physical=config["alpha_physical"],
            betas=config["betas"],
            contact_matrices=contact_matrices,
        )

    def get_raw_contact_matrices(
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
                contact_matrix = InteractiveSchool.get_raw_contact_matrix(
                    contact_matrix=contact_matrix,
                    proportion_physical=proportion_physical,
                    alpha_physical=alpha_physical,
                    characteristic_time=characteristic_time,
                )
            else:
                contact_matrix = InteractiveGroup.get_raw_contact_matrix(
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

    def create_infector_tensor(
        self,
        infectors_per_infection_per_subgroup,
        subgroup_sizes,
        contact_matrix,
        beta,
        delta_time,
    ):
        ret = {}
        for inf_id in infectors_per_infection_per_subgroup:
            infector_matrix = np.zeros_like(contact_matrix, dtype=np.float64)
            for subgroup_id in infectors_per_infection_per_subgroup[inf_id]:
                subgroup_trans_prob = sum(
                    infectors_per_infection_per_subgroup[inf_id][subgroup_id][
                        "trans_probs"
                    ]
                )
                for i in range(len(contact_matrix)):
                    subgroup_size = subgroup_sizes[subgroup_id]
                    if i == subgroup_id:
                        subgroup_size = max(1, subgroup_size - 1)
                    infector_matrix[i, subgroup_id] = (
                        contact_matrix[i, subgroup_id]
                        * subgroup_trans_prob
                        / subgroup_size
                    )
            ret[inf_id] = infector_matrix * beta * delta_time
        return ret

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
        to_blame_subgroups = []
        beta = self._get_interactive_group_beta(interactive_group)
        contact_matrix_raw = self.contact_matrices[group.spec]
        contact_matrix = interactive_group.get_processed_contact_matrix(
            contact_matrix_raw
        )
        infector_tensor = self.create_infector_tensor(
            interactive_group.infectors_per_infection_per_subgroup,
            interactive_group.subgroup_sizes,
            contact_matrix,
            beta,
            delta_time,
        )

        for (
            susceptible_subgroup_id,
            subgroup_susceptibles,
        ) in interactive_group.susceptibles_per_subgroup.items():
            (
                new_infected_ids,
                new_infection_ids,
                new_to_blame_subgroups,
            ) = self._time_step_for_subgroup(
                infector_tensor=infector_tensor,
                susceptible_subgroup_id=susceptible_subgroup_id,
                subgroup_susceptibles=subgroup_susceptibles,
            )
            infected_ids += new_infected_ids
            infection_ids += new_infection_ids
            to_blame_subgroups += new_to_blame_subgroups
        to_blame_ids = self._blame_individuals(
            to_blame_subgroups,
            infection_ids,
            interactive_group.infectors_per_infection_per_subgroup,
        )
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
        infector_tensor,
        susceptible_subgroup_id,
        subgroup_susceptibles,
    ):
        """
        Time step for one susceptible subgroup. We first compute the combined
        effective transmission probability of all the subgroups that contain infected
        people, and then run this effective transmission over the susceptible subgroup,
        to check who got infected.

        Parameters
        ----------
        """
        new_infected_ids = []
        new_infection_ids = []
        new_to_blame_subgroups = []
        infection_ids = list(infector_tensor.keys())
        for susceptible_id, susceptibility_dict in subgroup_susceptibles.items():
            infection_transmission_parameters = []
            for infection_id in infector_tensor:
                susceptibility = susceptibility_dict.get(infection_id, 1.0)
                infector_transmission = infector_tensor[infection_id][
                    susceptible_subgroup_id
                ].sum()
                infection_transmission_parameters.append(
                    infector_transmission * susceptibility
                )
            infection_id = self._gets_infected(
                np.array(infection_transmission_parameters), infection_ids
            )
            if infection_id is not None:
                new_infected_ids.append(susceptible_id)
                new_infection_ids.append(infection_id)
                new_to_blame_subgroups.append(
                    self._blame_subgroup(
                        infector_tensor[infection_id][susceptible_subgroup_id]
                    )
                )
        return new_infected_ids, new_infection_ids, new_to_blame_subgroups

    def _gets_infected(self, infection_transmission_parameters, infection_ids):
        total_exp = infection_transmission_parameters.sum()
        if random() < 1 - np.exp(-total_exp):
            if len(infection_ids) == 1:
                return infection_ids[0]
            return np.random.choice(
                infection_ids, p=infection_transmission_parameters / total_exp
            )

    def _blame_subgroup(self, vector):
        probs = vector / vector.sum()
        return np.random.choice(len(vector), p=probs)

    def _blame_individuals(
        self, to_blame_subgroups, infection_ids, infectors_per_infection_per_subgroup
    ):
        ret = []
        for infection_id, subgroup in zip(infection_ids, to_blame_subgroups):
            candidates_ids = infectors_per_infection_per_subgroup[infection_id][
                subgroup
            ]["ids"]
            candidates_probs = np.array(
                infectors_per_infection_per_subgroup[infection_id][subgroup][
                    "trans_probs"
                ]
            )
            candidates_probs /= candidates_probs.sum()
            ret.append(np.random.choice(candidates_ids, p=candidates_probs))
        return ret

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
