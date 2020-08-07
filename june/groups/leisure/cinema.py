import numpy as np
import pandas as pd
import yaml
from typing import List, Optional
from june.demography.geography import Areas, SuperArea, SuperAreas, Geography

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path

default_cinemas_coordinates_filename = data_path / "input/leisure/cinemas_per_super_area.csv"
default_config_filename = configs_path / "defaults/groups/leisure/cinemas.yaml"


class Cinema(SocialVenue):
    """
    cinemas are fun.
    """

    def __init__(self):
        super().__init__()


class Cinemas(SocialVenues):
    def __init__(self, cinemas, make_tree:bool = True):
        super().__init__(cinemas)
        if cinemas and make_tree:
            self.make_tree()

    @classmethod
    def for_super_areas(
        cls,
        super_areas: List[SuperArea],
        coordinates_filename: str = default_cinemas_coordinates_filename,
    ):
        cinemas_per_super_area = pd.read_csv(coordinates_filename)
        sa_names = [super_area.name for super_area in super_areas]
        cinemas_coordinates = cinemas_per_super_area.loc[
            cinemas_per_super_area.super_area.isin(sa_names), ["lat", "lon"]
        ]
        return cls.from_coordinates(cinemas_coordinates.values)

    @classmethod
    def for_areas(
        cls, areas: Areas, coordinates_filename: str = default_cinemas_coordinates_filename,
    ):
        super_areas = [area.super_area for area in areas]
        return cls.for_super_areas(super_areas, coordinates_filename)

    @classmethod
    def for_geography(
        cls,
        geography: Geography,
        coordinates_filename: str = default_cinemas_coordinates_filename,
    ):
        return cls.for_super_areas(geography.super_areas, coordinates_filename)

    @classmethod
    def from_coordinates(cls, coordinates: List[np.array], **kwargs):
        social_venues = list()
        for coord in coordinates:
            sv = Cinema()
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
    def from_config(cls, cinemas: Cinemas, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(cinemas, **config)
