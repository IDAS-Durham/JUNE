import numpy as np
import pandas as pd
import yaml

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path

default_cinemas_coordinates_filename = (
    data_path / "processed/leisure_data/cinemas.csv"
)
default_config_filename = configs_path / "defaults/groups/leisure/cinemas.yaml"


class Cinema(SocialVenue):
    """
    Pubs are fun.
    """

    def __init__(self):
        super().__init__()


class Cinemas(SocialVenues):
    def __init__(self, cinemas):
        super().__init__(cinemas)

    @classmethod
    def from_file(cls, cinemas_filename: str = default_cinemas_coordinates_filename):
        cinema_df = pd.read_csv(cinemas_filename)
        return cls.from_coordinates(cinema_coordinates)


class CinemaDistributor(SocialVenueDistributor):
    def __init__(
        self,
        cinemas: Cinemas,
        male_age_probabilities: dict = None,
        female_age_probabilities: dict = None,
        neighbours_to_consider=5,
        maximum_distance=5,
        weekend_boost: float = 2.0,
    ):
        super().__init__(
            cinemas,
            male_age_probabilities,
            female_age_probabilities,
            neighbours_to_consider,
            maximum_distance,
            weekend_boost,
        )

    @classmethod
    def from_config(cls, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(**config)


