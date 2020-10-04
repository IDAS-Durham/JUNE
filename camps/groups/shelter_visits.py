import numpy as np
import pandas as pd
import yaml
from itertools import chain
from random import randint, shuffle
from june.geography import Areas, SuperAreas
from june.groups.leisure.social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path

from camps.paths import camp_data_path, camp_configs_path
from camps.groups import Shelter, Shelters

default_config_filename = camp_configs_path / "defaults/groups/shelter_visits.yaml"


class SheltersVisitsDistributor(SocialVenueDistributor):
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
    def from_config(cls, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(**config)

    def link_shelters_to_shelters(self, super_areas):
        """
        Links people between shelters. Strategy: We pair each shelter with 0, 1, or 2 other shelters (with equal prob.). The shelter of the former then has a probability of visiting the shelter of the later 
        at every time step.

        Parameters
        ----------
        super_areas
            list of super areas
        """
        for super_area in super_areas:
            shelters_super_area = list(
                chain.from_iterable(area.shelters for area in super_area.areas)
            )
            shuffle(shelters_super_area)
            for shelter in shelters_super_area:
                if shelter.n_families == 0:
                    continue
                shelters_to_link_n = randint(0, 3)
                shelters_to_visit = []
                for _ in range(shelters_to_link_n):
                    shelter_idx = randint(0, len(shelters_super_area) - 1)
                    shelter_to_visit = shelters_super_area[shelter_idx]
                    if shelter_to_visit.id == shelter.id or shelter_to_visit.n_families== 0:
                        continue
                    shelters_to_visit.append(shelter_to_visit)
                if shelters_to_visit:
                    shelter.shelters_to_visit = tuple(shelters_to_visit)

    def get_possible_venues_for_household(self, household: Shelter):
        if household.shelters_to_visit is None:
            return ()
        return household.shelters_to_visit

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
