import numpy as np
import pandas as pd
import yaml
from typing import List

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path
from june.geography import SuperArea

default_config_filename = configs_path / "defaults/groups/leisure/groceries.yaml"


class Grocery(SocialVenue):
    def __init__(self):
        super().__init__()


class Groceries(SocialVenues):
    def __init__(self, groceries: List[Grocery]):
        super().__init__(groceries)

    @classmethod
    def for_super_areas(cls, super_areas: List[SuperArea], venues_per_super_area=1):
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
            for _ in range(venues_per_super_area):
                grocery = Grocery()
                grocery.super_area = super_area
                super_area.groceries.append(grocery)
                groceries.append(grocery)
        return cls(groceries)

class GroceryDistributor(SocialVenueDistributor):
    def __init__(
        self,
        groceries: Groceries,
        male_age_probabilities: dict = None,
        female_age_probabilities: dict = None,
        weekend_boost: float = 2.0,
    ):
        super().__init__(
            groceries,
            male_age_probabilities,
            female_age_probabilities,
            weekend_boost,
        )

    @classmethod
    def from_config(cls, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(**config)

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
