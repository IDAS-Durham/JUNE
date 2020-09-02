import numpy as np
import pandas as pd
import yaml
from typing import List

from june.groups.leisure.social_venue import SocialVenue, SocialVenues, SocialVenueError
from june.groups.leisure.social_venue_distributor import SocialVenueDistributor
from camps.paths import camp_configs_path
from june.demography.geography import SuperArea, Area
from june.groups import Household

default_config_filename = camp_configs_path / "defaults/groups/pump_latrine.yaml"

class PumpLatrine(SocialVenue):
    def __init__(self, max_size=np.inf):
        self.max_size = max_size
        super().__init__()

class PumpLatrines(SocialVenues):
    def __init__(self, pump_latrines: List[PumpLatrine]):
        super().__init__(pump_latrines, make_tree=False)

    @classmethod
    def for_areas(cls, areas: List[Area], venues_per_capita=1/(100+35/2), max_size=10):
        pump_latrines = []
        for area in areas:
            area_population = len(area.people)
            for _ in range(0, int(np.ceil(venues_per_capita * area_population))):
                pump_latrine = PumpLatrine(max_size)
                area.pump_latrines.append(pump_latrine)
                pump_latrines.append(pump_latrine)
        return cls(pump_latrines)

class PumpLatrineDistributor(SocialVenueDistributor):
    def __init__(
            self,
            pump_latrines: PumpLatrines,
            male_age_probabilities: dict = None,
            female_age_probabilities: dict = None,
            neighbours_to_consider=5,
            maximum_distance=5,
            weekend_boost: float = 1.0,
            drags_household_probability = 0.
    ):
        super().__init__(
            social_venues=pump_latrines,
            male_age_probabilities=male_age_probabilities,
            female_age_probabilities=female_age_probabilities,
            neighbours_to_consider=neighbours_to_consider,
            maximum_distance=maximum_distance,
            weekend_boost=weekend_boost,
            drags_household_probability=drags_household_probability
        )

    @classmethod
    def from_config(cls, pump_latrines, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(pump_latrines, **config)

    def get_social_venue_for_person(self, person):
        """
        We select a random pump or latrine from the person area.
        """
        venue = np.random.choice(person.area.pump_latrines)
        return venue

    def get_possible_venues_for_household(self, household: Household):
        venue = np.random.choice(household.area.pump_latrines)
        return [venue]
