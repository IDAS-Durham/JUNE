import numpy as np
import pandas as pd
import yaml
from typing import List

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path
from june.demography.geography import Geography

default_pub_coordinates_filename = (
    data_path / "geographical_data/pubs_uk24727_latlong.txt"
)
default_config_filename = configs_path / "defaults/groups/leisure/pubs.yaml"


class Pub(SocialVenue):
    """
    Pubs are fun.
    """

    def __init__(self):
        super().__init__()


class Pubs(SocialVenues):
    def __init__(self, pubs: List[Pub]):
        super().__init__(pubs)

    @classmethod
    def for_geography(
        cls,
        geography: Geography,
        coordinates_filename: str = default_pub_coordinates_filename,
    ):
        pub_coordinates = np.loadtxt(coordinates_filename)
        return cls.from_coordinates(pub_coordinates, geography.areas)


class PubDistributor(SocialVenueDistributor):
    def __init__(
        self,
        pubs: Pubs,
        male_age_probabilities: dict = None,
        female_age_probabilities: dict = None,
        neighbours_to_consider=5,
        maximum_distance=5,
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
    def from_config(cls, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(**config)
