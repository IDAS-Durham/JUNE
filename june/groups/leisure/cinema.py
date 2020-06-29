import numpy as np
import pandas as pd
import yaml
from typing import List, Optional
from june.demography.geography import Areas

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path

default_cinemas_coordinates_filename = data_path / "input/leisure/cinemas.csv"
default_config_filename = configs_path / "defaults/groups/leisure/cinemas.yaml"


class Cinema(SocialVenue):
    """
    Pubs are fun.
    """

    def __init__(self, n_seats=np.inf):
        super().__init__()
        self.max_size = n_seats


class Cinemas(SocialVenues):
    def __init__(self, cinemas, make_tree:bool = True):
        super().__init__(cinemas)
        if len(cinemas) != 0 and make_tree:
            self.make_tree()

    @classmethod
    def for_areas(
        cls,
        areas: Areas,
        coordinates_filename: str = default_cinemas_coordinates_filename,
        max_distance_to_area=5,
    ):
        cinemas_df = pd.read_csv(coordinates_filename)
        coordinates = cinemas_df.loc[:, ["latitude", "longitude"]].values
        n_seats = cinemas_df.loc[:, ["seats"]].values
        return cls.from_coordinates(
            coordinates,
            n_seats,
            areas,
            max_distance_to_area=max_distance_to_area,
        )
    @classmethod
    def for_geography(
        cls,
        geography,
        coordinates_filename: str = default_cinemas_coordinates_filename,
        max_distance_to_area=5,
    ):
        return cls.for_areas(
            geography.areas,
            coordinates_filename,
            max_distance_to_area,
        )

    @classmethod
    def from_coordinates(
        cls,
        coordinates: List[np.array],
        seats: List[int],
        areas: Optional[Areas] = None,
        max_distance_to_area=5,
        **kwargs
    ):
        if areas is not None:
            _, distances = areas.get_closest_areas(
                coordinates, k=1, return_distance=True
            )
            distances_close = np.where(distances < max_distance_to_area)
            coordinates = coordinates[distances_close]
        social_venues = list()
        for coord, n_seats in zip(coordinates, seats):
            sv = Cinema(int(n_seats))
            sv.coordinates = coord
            social_venues.append(sv)
        return cls(social_venues, **kwargs)


class CinemaDistributor(SocialVenueDistributor):
    def __init__(
        self,
        cinemas: Cinemas,
        male_age_probabilities: dict = None,
        female_age_probabilities: dict = None,
        neighbours_to_consider=5,
        maximum_distance=5,
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
    def from_config(cls, cinemas: Cinemas, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(cinemas, **config)
