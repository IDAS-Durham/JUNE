import yaml
from random import shuffle, randint
import numpy as np
from numpy.random import choice

from june.groups.leisure import SocialVenueDistributor
from june.paths import configs_path
from june.utils import random_choice_numba

default_config_filename = configs_path / "defaults/groups/leisure/visits.yaml"


class ResidenceVisitsDistributor(SocialVenueDistributor):
    """
    This is a social distributor specific to model visits between residences,
    ie, visits between households or to care homes. The meaning of the parameters
    is the same as for the SVD. Residence visits are not decied on neighbours or distances
    so we ignore some parameters.
    """

    def __init__(
        self,
        residence_type_probabilities,
        times_per_week,
        hours_per_day,
        drags_household_probability=0,
    ):
        # it is necessary to make them arrays for performance
        self.residence_type_probabilities = residence_type_probabilities
        self.policy_reductions = {}
        super().__init__(
            social_venues=None,
            times_per_week=times_per_week,
            hours_per_day=hours_per_day,
            drags_household_probability=drags_household_probability,
            neighbours_to_consider=None,
            maximum_distance=None,
            leisure_subgroup_type=None,
        )

    @classmethod
    def from_config(cls, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(**config)

    def link_households_to_households(self, super_areas):
        """
        Links people between households. Strategy: We pair each household with 0, 1,
        or 2 other households (with equal prob.). The household of the former then
        has a probability of visiting the household of the later
        at every time step.

        Parameters
        ----------
        super_areas
            list of super areas
        """
        for super_area in super_areas:
            households_in_super_area = [
                household for area in super_area.areas for household in area.households
            ]
            for household in households_in_super_area:
                if household.n_residents == 0:
                    continue
                households_to_link_n = randint(2, 4)
                households_to_visit = []
                n_linked = 0
                while n_linked < households_to_link_n:
                    house_idx = randint(0, len(households_in_super_area) - 1)
                    house = households_in_super_area[house_idx]
                    if house.id == household.id or not house.residents:
                        continue
                    households_to_visit.append(house)
                    n_linked += 1
                if households_to_visit:
                    household.residences_to_visit["household"] = tuple(
                        households_to_visit
                    )

    def link_households_to_care_homes(self, super_areas):
        """
        Links households and care homes in the giving super areas. For each care home,
        we find a random house in the super area and link it to it.
        The house needs to be occupied by a family, or a couple.

        Parameters
        ----------
        super_areas
            list of super areas
        """
        for super_area in super_areas:
            households_super_area = []
            for area in super_area.areas:
                households_super_area += [
                    household
                    for household in area.households
                    if household.type in ["families", "ya_parents", "nokids"]
                ]
            shuffle(households_super_area)
            for area in super_area.areas:
                if area.care_home is not None:
                    people_in_care_home = [
                        person for person in area.care_home.residents
                    ]
                    for i, person in enumerate(people_in_care_home):
                        household = households_super_area[i]
                        household.residences_to_visit["care_home"] = (
                            *household.residences_to_visit["care_home"],
                            area.care_home,
                        )

    def get_leisure_group(self, person):
        residence_types = list(person.residence.group.residences_to_visit.keys())
        if not residence_types:
            return
        if len(residence_types) == 0:
            which_type = residence_types[0]
        else:
            if self.policy_reductions:
                probabilities = self.policy_reductions
            else:
                probabilities = self.residence_type_probabilities
            residence_type_probabilities = np.array(
                [probabilities[residence_type] for residence_type in residence_types]
            )
            residence_type_probabilities = (
                residence_type_probabilities / residence_type_probabilities.sum()
            )
            type_sample = random_choice_numba(
                tuple(range(len(residence_type_probabilities))),
                residence_type_probabilities,
            )
            which_type = residence_types[type_sample]
        candidates = person.residence.group.residences_to_visit[which_type]
        n_candidates = len(candidates)
        if n_candidates == 0:
            return
        elif n_candidates == 1:
            group = candidates[0]
        else:
            group = candidates[randint(0, n_candidates - 1)]
        return group

    def get_poisson_parameter(
        self,
        sex,
        age,
        day_type,
        working_hours,
        region=None,
        policy_reduction=None,
    ):
        """
        This differs from the super() implementation in that we do not allow
        visits during working hours as most people are away.
        """
        if working_hours:
            return 0
        return super().get_poisson_parameter(
            sex=sex,
            age=age,
            day_type=day_type,
            working_hours=working_hours,
            region=region,
            policy_reduction=policy_reduction,
        )
