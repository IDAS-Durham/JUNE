import numpy as np
import pandas as pd
import yaml
from typing import List
from june.demography.geography import Areas, SuperArea, SuperAreas, Geography

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path

default_cinemas_coordinates_filename = (
    data_path / "input/leisure/cinemas_per_super_area.csv"
)
default_config_filename = configs_path / "defaults/groups/leisure/cinemas.yaml"


class Cinema(SocialVenue):
    """
    cinemas are fun.
    """

    def __init__(self):
        super().__init__()


class Cinemas(SocialVenues):
    default_coordinates_filename = default_cinemas_coordinates_filename


class CinemaDistributor(SocialVenueDistributor):
    def __init__(
        self,
        cinemas: Cinemas,
        male_age_probabilities: dict = None,
        female_age_probabilities: dict = None,
        neighbours_to_consider=5,
        maximum_distance=15,
        weekend_boost: float = 2.0,
        drags_household_probability=0.5,
    ):
        super().__init__(
            social_venues=cinemas,
            male_age_probabilities=male_age_probabilities,
            female_age_probabilities=female_age_probabilities,
            neighbours_to_consider=neighbours_to_consider,
            maximum_distance=maximum_distance,
            weekend_boost=weekend_boost,
            drags_household_probability=drags_household_probability,
        )

    @classmethod
    def from_config(
        cls, cinemas: Cinemas, config_filename: str = default_config_filename
    ):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(cinemas, **config)
