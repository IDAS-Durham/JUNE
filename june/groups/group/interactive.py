from collections import defaultdict
import numpy as np
import numba as nb


@nb.jit(nopython=True)
def _get_processed_contact_matrix(contact_matrix, alpha_physical, proportion_physical):
    """
    Computes the contact matrix used in the interaction,
    which boosts the physical contacts by a factor.

    Parameters
    ----------
    - contact_matrix : contact matrix
    - alpha_physical : relative weight of physical contacts respect to the normal ones.
    (1 = same as normal).
    - proportion_physical : proportion of physical contacts.
    """
    return contact_matrix * (1.0 + (alpha_physical - 1.0) * proportion_physical)


class InteractiveGroup:
    """
    Extracts the necessary information about a group to perform an interaction time
    step over it. This step is necessary, since all the information is stored in numpy
    arrays that allow for efficient computation.

    Parameters
    ----------
    - group : group that we want to prepare for interaction.
    """

    def __init__(self, group: "Group", people_from_abroad=None):
        """
        This function is very long to avoid function calls for performance reasons.
        InteractiveGroups are created millions of times. Given a group, we need to extract:
        - ids of the people that can infect (infector).
        - ids of the people that can be infected (susceptible).
        - probabilities of transmission of the infectors.
        - susceptibilities of the susceptible.
        - indices of the subgroups that contain infectors.
        - sizes of the subgroups that contain infectors.
        - indices of the subgroups that contain susceptible.
        - spec of the group
        - super area of the group (for geo attributes like local regional compliances)
        """
        people_from_abroad = people_from_abroad or {}
        self.group = group
        self.infectors_per_infection_per_subgroup = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )  # maps virus variant -> subgroup -> infectors -> {infector ids, transmission probs}
        self.susceptibles_per_subgroup = defaultdict(
            dict
        )  # maps subgroup -> susceptible id -> {variant -> susceptibility}
        self.subgroup_sizes = {}
        group_size = 0

        for subgroup_index, subgroup in enumerate(group.subgroups):
            subgroup_size = len(subgroup.people)
            if subgroup.subgroup_type in people_from_abroad:
                people_abroad_data = people_from_abroad[subgroup.subgroup_type]
                people_abroad_ids = people_abroad_data.keys()
                subgroup_size += len(people_abroad_ids)
            else:
                people_abroad_data = None
                people_abroad_ids = []
            if subgroup_size == 0:
                continue
            self.subgroup_sizes[subgroup_index] = subgroup_size
            group_size += subgroup_size

            # Get susceptible people
            # local
            for person in subgroup:
                if not person.infected:
                    self.susceptibles_per_subgroup[subgroup_index][
                        person.id
                    ] = person.immunity.susceptibility_dict
            # from abroad
            for id in people_abroad_ids:
                if people_abroad_data[id]["susc"]:
                    dd = {
                        key: value
                        for key, value in zip(
                            people_abroad_data[id]["immunity_inf_ids"],
                            people_abroad_data[id]["immunity_suscs"],
                        )
                    }
                    self.susceptibles_per_subgroup[subgroup_index][id] = dd

            # Get infectors
            for person in subgroup:
                if person.infection is not None:
                    infection_id = person.infection.infection_id()
                    self.infectors_per_infection_per_subgroup[infection_id][
                        subgroup_index
                    ]["ids"].append(person.id)
                    self.infectors_per_infection_per_subgroup[infection_id][
                        subgroup_index
                    ]["trans_probs"].append(person.infection.transmission.probability)
            for id in people_abroad_ids:
                if people_abroad_data[id]["inf_id"] != 0:
                    infection_id = people_abroad_data[id]["inf_id"]
                    self.infectors_per_infection_per_subgroup[infection_id][
                        subgroup_index
                    ]["ids"].append(id)
                    self.infectors_per_infection_per_subgroup[infection_id][
                        subgroup_index
                    ]["trans_probs"].append(people_abroad_data[id]["inf_prob"])
        self.must_timestep = self.has_susceptible and self.has_infectors
        self.size = group_size

    @classmethod
    def get_raw_contact_matrix(
        cls, contact_matrix, alpha_physical, proportion_physical, characteristic_time
    ):
        """
        Returns the processed contact matrix, by default it returns the input,
        but children of this class will interact differently.
        """
        processed_contact_matrix = contact_matrix * (
            1.0 + (alpha_physical - 1.0) * proportion_physical
        )
        processed_contact_matrix *= 24 / characteristic_time
        return processed_contact_matrix

    def get_processed_beta(self, betas, beta_reductions):
        """
        Returns the processed contact intensity, by taking into account the policies
        beta reductions and regional compliance. This is a group method as different interactive
        groups may choose to treat this differently.
        """
        beta = betas[self.spec]
        beta_reduction = beta_reductions.get(self.spec, 1.0)
        try:
            regional_compliance = self.super_area.region.regional_compliance
        except AttributeError:
            regional_compliance = 1
        try:
            lockdown_tier = self.super_area.region.policy["lockdown_tier"]
            if lockdown_tier is None:
                lockdown_tier = 1
        except:
            lockdown_tier = 1
        if int(lockdown_tier) == 4:
            tier_reduction = 0.5
        else:
            tier_reduction = 1.0

        return beta * (1 + regional_compliance * tier_reduction * (beta_reduction - 1))

    def get_processed_contact_matrix(self, contact_matrix):
        return contact_matrix

    @property
    def spec(self):
        return self.group.spec

    @property
    def super_area(self):
        return self.group.super_area

    @property
    def regional_compliance(self):
        return self.group.super_area.region.regional_compliance

    @property
    def has_susceptible(self):
        return bool(self.susceptibles_per_subgroup)

    @property
    def has_infectors(self):
        return bool(self.infectors_per_infection_per_subgroup)
