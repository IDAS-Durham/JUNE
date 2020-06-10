import numpy as np
import pandas as pd
import yaml
from typing import List

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path
from june.demography.geography import SuperArea, Area

default_config_filename = configs_path / "defaults/groups/leisure/pumplatrines.yaml"

class PumpLatrine(SocialVenue):
    def __init__(self, max_size=10):
        self.max_size = max_size
        super().__init__()

class PumpLatrines(SocialVenues):
    def __init__(self, pumplatrines: List[PumpLatrine]):
        super().__init__(pumplatrines)

    @classmethod
    def for_areas(cls, areas: List[Area], venues_per_capita=1/(100+35/2), max_size=10):
        pumplatrines = []
        for area in areas:
            area_population = len(area.people)
            for _ in range(0, int(np.ceil(venues_per_capita * area_population))):
                pumplatrine = PumpLatrine(max_size)
                area.pumplatrines.append(pumplatrine)
                pumplatrines.append(pumplatrine)
        return cls(pumplatrines)

class PumpLatrineDistributor(SocialVenueDistributor):
    def __init__(
            self,
            pumplatrines: PumpLatrines,
            male_age_probabilities: dict = None,
            female_age_probabilities: dict = None,
            weekend_boost: float = 1.0,
            drags_household_probability = 0.
    ):
        super().__init__(
            social_venues=pumplatrines,
            male_age_probabilities=male_age_probabilities,
            female_age_probabilities=female_age_probabilities,
            weekend_boost=weekend_boost,
            drags_household_probability=drags_household_probability
        )

    @classmethod
    def from_config(cls, pumplatrines, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(pumplatrines, **config)

    def get_social_venue_for_person(self, person):
        """
        We select a random pump or latrine from the person area.
        """
        venue = np.random.choice(person.area.pumplatrines)
        return venue
