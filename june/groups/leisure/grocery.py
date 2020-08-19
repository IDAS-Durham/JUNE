import numpy as np
import pandas as pd
import yaml
from typing import List

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path
from june.demography.geography import SuperArea, Areas, Geography

default_config_filename = configs_path / "defaults/groups/leisure/groceries.yaml"
default_groceries_coordinates_filename = (
    data_path / "input/leisure/groceries_per_super_area.csv"
)


class Grocery(SocialVenue):
    def __init__(self):
        super().__init__()


class Groceries(SocialVenues):
    default_coordinates_filename = default_groceries_coordinates_filename


class GroceryDistributor(SocialVenueDistributor):
    def __init__(
        self,
        groceries: Groceries,
        male_age_probabilities: dict = None,
        female_age_probabilities: dict = None,
        neighbours_to_consider=10,
        maximum_distance=10,
        weekend_boost: float = 2.0,
        drags_household_probability=0.5,
    ):
        super().__init__(
            social_venues=groceries,
            male_age_probabilities=male_age_probabilities,
            female_age_probabilities=female_age_probabilities,
            weekend_boost=weekend_boost,
            drags_household_probability=drags_household_probability,
            neighbours_to_consider=neighbours_to_consider,
            maximum_distance=maximum_distance,
        )

    @classmethod
    def from_config(cls, groceries, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(groceries, **config)
