import numpy as np
import pandas as pd
import yaml
from random import randint, shuffle
from june.geography import Areas, SuperAreas
from june.groups import CareHomes, Households, Household, CareHome

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path

default_config_filename = configs_path / "defaults/groups/leisure/care_home_visits.yaml"


class CareHomeVisitsDistributor(SocialVenueDistributor):
    def __init__(
        self,
        male_age_probabilities: dict = None,
        female_age_probabilities: dict = None,
        neighbours_to_consider=None,
        maximum_distance=None,
        weekend_boost: float = 2.0,
        drags_household_probability=1.0,
    ):
        super().__init__(
            social_venues=None,
            male_age_probabilities=male_age_probabilities,
            female_age_probabilities=female_age_probabilities,
            neighbours_to_consider=neighbours_to_consider,
            maximum_distance=maximum_distance,
            weekend_boost=weekend_boost,
            drags_household_probability=drags_household_probability,
        )

    @classmethod
    def from_config(
        cls, config_filename: str = default_config_filename
    ):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(**config)

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
                        if households_super_area[i].care_homes_to_visit is None:
                            households_super_area[i].care_homes_to_visit = (area.care_home,)
                        else:
                            households_super_area[i].care_homes_to_visit = tuple(
                                (
                                    *households_super_area[i].care_homes_to_visit,
                                    area.care_home,
                                )
                            )

    def get_possible_venues_for_household(self, household: Household):
        if household.relatives_in_care_homes is None:
            return ()
        return tuple(
            relative.residence.group
            for relative in household.relatives_in_care_homes
            if relative.dead is False
        )

    def get_social_venue_for_person(self, person):
        care_homes_to_visit = person.residence.group.care_homes_to_visit
        if care_homes_to_visit is None:
            return None
        return care_homes_to_visit[
            randint(0, len(care_homes_to_visit) - 1)
        ]

    def get_poisson_parameter(self, sex, age, is_weekend: bool = False):
        """
        Poisson parameter (lambda) of a person going to one social venue according to their
        age and sex and the distribution of visitors in the venue.

        Parameters
        ----------
        person
            an instance of Person
        delta_t
            interval of time in units of days
        is_weekend
            whether it is a weekend or not
        """
        if sex == "m":
            probability = self.male_probabilities[age]
        else:
            probability = self.female_probabilities[age]
        if is_weekend:
            probability = probability * self.weekend_boost
        return probability

    def get_leisure_subgroup_type(self, person):
        return CareHome.SubgroupType.visitors
