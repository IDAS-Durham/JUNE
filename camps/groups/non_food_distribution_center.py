import numpy as np
import pandas as pd
import yaml
from typing import List, Optional
from june.demography.geography import Areas

from june.groups.leisure.social_venue import SocialVenue, SocialVenues, SocialVenueError
from june.groups.leisure.social_venue_distributor import SocialVenueDistributor
from camps.paths import camp_data_path, camp_configs_path

default_nfdistributioncenters_coordinates_filename = camp_data_path / "input/activities/non_food_distribution_center.csv"
default_config_filename = camp_configs_path / "defaults/groups/non_food_distribution_center.yaml"

class NFDistributionCenter(SocialVenue):
    def __init__(self, max_size=np.inf):
        super().__init__()
        self.max_size = max_size


class NFDistributionCenters(SocialVenues):
    def __init__(self, nfdistributioncenters, make_tree:bool = True):
        super().__init__(nfdistributioncenters)
        if len(nfdistributioncenters) != 0 and make_tree:
            self.make_tree()

    @classmethod
    def for_areas(
        cls,
        areas: Areas,
        coordinates_filename: str = default_nfdistributioncenters_coordinates_filename,
        max_distance_to_area=5,
        max_size=np.inf,
    ):
        nfdistributioncenters_df = pd.read_csv(coordinates_filename)
        coordinates = nfdistributioncenters_df.loc[:, ["latitude", "longitude"]].values
        return cls.from_coordinates(
            coordinates,
            max_size,
            areas,
            max_distance_to_area=max_distance_to_area,

        )
    
    @classmethod
    def for_geography(
        cls,
        geography,
        coordinates_filename: str = default_nfdistributioncenters_coordinates_filename,
        max_distance_to_area=5,
        max_size=np.inf,
    ):
        return cls.for_areas(
            coordinates_filename=coordinates_filename,
            max_size=max_size,
            areas =geography.areas,
            max_distance_to_area=max_distance_to_area,
        )

    @classmethod
    def from_coordinates(
        cls,
        coordinates: List[np.array],
        max_size = np.inf,
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
        for coord in coordinates:
            sv = NFDistributionCenter(max_size)
            sv.coordinates = coord
            social_venues.append(sv)
        return cls(social_venues, **kwargs)


class NFDistributionCenterDistributor(SocialVenueDistributor):
    def __init__(
        self,
        nfdistributioncenters: NFDistributionCenters,
        male_age_probabilities: dict = None,
        female_age_probabilities: dict = None,
        neighbours_to_consider=5,
        maximum_distance=5,
        weekend_boost: float = 1.0,
        drags_household_probability=0.3,
    ):
        super().__init__(
            social_venues=nfdistributioncenters,
            male_age_probabilities=male_age_probabilities,
            female_age_probabilities=female_age_probabilities,
            neighbours_to_consider=neighbours_to_consider,
            maximum_distance=maximum_distance,
            weekend_boost=weekend_boost,
            drags_household_probability=drags_household_probability,
        )

    @classmethod
    def from_config(cls, nfdistributioncenters: NFDistributionCenters, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(nfdistributioncenters, **config)
