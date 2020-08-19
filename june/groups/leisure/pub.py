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
    def __init__(self, pubs: List[Pub], make_tree=True):
        super().__init__(pubs)
        if make_tree:
            self.make_tree()

    @classmethod
    def for_super_areas(
        cls,
        super_areas: List[SuperArea],
        coordinates_filename: str = default_pub_coordinates_filename,
    ):
        pubs_per_super_area = pd.read_csv(coordinates_filename)
        sa_names = [super_area.name for super_area in super_areas]
        pubs_coordinates = pubs_per_super_area.loc[
            pubs_per_super_area.super_area.isin(sa_names), ["lat", "lon"]
        ]
        return cls.from_coordinates(pubs_coordinates.values)

    @classmethod
    def for_areas(
        cls, areas: Areas, coordinates_filename: str = default_pub_coordinates_filename,
    ):
        super_areas = [area.super_area for area in areas]
        return cls.for_super_areas(super_areas, coordinates_filename)

    @classmethod
    def for_geography(
        cls,
        geography: Geography,
        coordinates_filename: str = default_pub_coordinates_filename,
    ):
        return cls.for_super_areas(geography.super_areas, coordinates_filename)

    @classmethod
    def from_coordinates(cls, coordinates: List[np.array], **kwargs):
        social_venues = []
        for coord in coordinates:
            sv = Pub()
            sv.coordinates = coord
            social_venues.append(sv)
        return cls(social_venues, **kwargs)


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
