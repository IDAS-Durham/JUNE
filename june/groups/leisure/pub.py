import numpy as np
import pandas as pd
import yaml
from typing import List

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path
from june.demography.geography import Geography
from june.demography.geography import Area, Areas, SuperArea, SuperAreas

default_pub_coordinates_filename = data_path / "input/leisure/pubs_per_super_area.csv"
default_config_filename = configs_path / "defaults/groups/leisure/pubs.yaml"


class Pub(SocialVenue):
    """
    Pubs are fun.
    """

    def __init__(self):
        super().__init__()


class Pubs(SocialVenues):
    default_coordinates_filename = default_pub_coordinates_filename


class PubDistributor(SocialVenueDistributor):
    def __init__(
        self,
        pubs: Pubs,
        male_age_probabilities: dict = None,
        female_age_probabilities: dict = None,
        neighbours_to_consider=10,
        maximum_distance=10,
        weekend_boost: float = 2.0,
        drags_household_probability=0.5,
    ):
        super().__init__(
            social_venues=pubs,
            male_age_probabilities=male_age_probabilities,
            female_age_probabilities=female_age_probabilities,
            neighbours_to_consider=neighbours_to_consider,
            maximum_distance=maximum_distance,
            weekend_boost=weekend_boost,
            drags_household_probability=drags_household_probability,
        )

    @classmethod
    def from_config(cls, pubs: Pubs, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(pubs, **config)
