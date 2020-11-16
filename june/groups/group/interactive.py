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

        self.infector_ids = []
        self.susceptible_ids = []
        self.infector_transmission_probabilities = []
        self.susceptible_susceptibilities = []
        self.subgroups_with_infectors = []
        self.subgroups_with_infectors_sizes = []
        self.subgroups_with_susceptible = []

        has_susceptible = False
        has_infector = False
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
            group_size += subgroup_size

            # get susceptible people in subgroup
            local_subgroup_susceptible_people = [
                person for person in subgroup if person.susceptible
            ]
            subgroup_susceptible_ids = [
                person.id for person in local_subgroup_susceptible_people 
            ]
            subgroup_susceptible_ids += [
                id
                for id in people_abroad_ids
                if people_abroad_data[id]["susc"] > 0.0
            ]

            if subgroup_susceptible_ids:
                # store subgroup id and susceptibilities
                has_susceptible = True
                self.subgroups_with_susceptible.append(subgroup_index)
                subgroup_susceptibilities = [
                    person.susceptibility for person in local_subgroup_susceptible_people 
                ]
                subgroup_susceptibilities += [
                    people_abroad_data[id]["susc"]
                    for id in people_abroad_ids
                    if people_abroad_data[id]["susc"] > 0.0
                ]
                self.susceptible_ids.append(subgroup_susceptible_ids)
                self.susceptibilities.append(subgroup_susceptibilities)

            # get infectious people in subgroup
            local_subgroup_infectors = [
                person
                for person in subgroup
                if person.infection is not None
                and person.infection.transmission.probability > 0
            ]
            subgroup_infector_ids = [
                person.id for person in local_subgroup_infectors
            ]
            subgroup_infector_ids += [
                id
                for id in people_abroad_ids
                if people_abroad_data[id]["inf_prob"] > 0
            ]
            if subgroup_infector_ids:
                # has infected
                has_infector = True
                self.subgroups_with_infectors.append(subgroup_index)
                subgroup_infector_trans_prob = [
                    person.infection.transmission.probability
                    for person in local_subgroup_infectors 
                ]
                subgroup_infector_trans_prob += [
                    people_abroad_data[id]["inf_prob"]
                    for id in people_abroad_ids
                    if people_abroad_data[id]["inf_prob"] > 0
                ]
                self.infector_transmission_probabilities.append(subgroup_infector_trans_prob)
                self.infector_ids.append(subgroup_infector_ids)
                self.subgroups_with_infectors_sizes.append(subgroup_size)
        self.must_timestep = has_susceptible and has_infector
        self.size = group_size
        if self.must_timestep is False:
            return

    @classmethod
    def get_processed_contact_matrix(
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

    def get_processed_beta(self, beta):
        """
        Returns the processed contact intensity, by default it returns the input,
        but children of this class will interact differently.
        """
        return beta

    def get_contacts_between_subgroups(
        self, contact_matrix, subgroup_1_idx, subgroup_2_idx
    ):
        """
        Returns the number of contacts between subgroup 1 and 2,
        with their indices given as input. By default, this just
        indexes the contact matrix, but for specific groups like schools,
        this is used to handle interaction between classes of same year groups.
        """
        return contact_matrix[subgroup_1_idx][subgroup_2_idx]

    @property
    def spec(self):
        return self.group.spec

    @property
    def super_area(self):
        return self.group.super_area
