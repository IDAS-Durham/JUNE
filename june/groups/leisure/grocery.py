import numpy as np
import pandas as pd
import yaml
from typing import List

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path
from june.demography.geography import SuperArea

default_config_filename = configs_path / "defaults/groups/leisure/groceries.yaml"


class Grocery(SocialVenue):
    def __init__(self, max_size=100):
        self.max_size = max_size
        super().__init__()


class Groceries(SocialVenues):
    def __init__(self, groceries: List[Grocery]):
        super().__init__(groceries)

    @classmethod
    def for_super_areas(cls, super_areas: List[SuperArea], venues_per_capita=1/760, max_size=100):
        """
        Generates social venues in the given super areas.

        Parameters
        ----------
        super_areas
            list of areas to generate the venues in
        venues_per_super_area
            how many venus per super_area to generate
        """
        groceries = []
        for super_area in super_areas:
            area_population = len(super_area.people)
            print(area_population)
            for _ in range(0, int(np.ceil(venues_per_capita * area_population))):
                grocery = Grocery(max_size)
                groceries.append(grocery)
        print("gorceries")
        print(groceries)
        return cls(groceries)


class GroceryDistributor(SocialVenueDistributor):
    def __init__(
        self,
        groceries: Groceries,
        male_age_probabilities: dict = None,
        female_age_probabilities: dict = None,
        weekend_boost: float = 2.0,
        drags_household_probability = 0.5
    ):
        super().__init__(
            social_venues=groceries,
            male_age_probabilities=male_age_probabilities,
            female_age_probabilities=female_age_probabilities,
            weekend_boost=weekend_boost,
            drags_household_probability=drags_household_probability
        )

    @classmethod
    def from_config(cls, groceries, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(groceries, **config)

    def add_person_to_social_venue(self, person):
        """
        Adds a person to one of the social venues in the distributor. To decide, we select randomly
        from a certain number of neighbours, or the closest venue if the distance is greater than
        the maximum_distance.

        Parameters
        ----------
        person
            
        """
        venue = np.random.choice(person.area.super_area.groceries) 
        venue.add(person)
