import numpy as np
import pandas as pd
import yaml
from typing import List, Optional
from june.demography.geography import Areas, SuperAreas
from june.groups import CareHomes, Households

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path

default_config_filename = configs_path / "defaults/groups/leisure/residence_visits.yaml"


class VisitsDistributor(SocialVenueDistributor):
    def __init__(
        self,
        super_areas: SuperAreas,
        male_age_probabilities: dict = None,
        female_age_probabilities: dict = None,
        neighbours_to_consider=None,
        maximum_distance=None,
        weekend_boost: float = 2.0,
        drags_household_probability=1.0,
    ):
        super().__init__(
            social_venues=None,
            male_age_probabilities=male_age_probabilities,
            female_age_probabilities=female_age_probabilities,
            neighbours_to_consider=neighbours_to_consider,
            maximum_distance=maximum_distance,
            weekend_boost=weekend_boost,
            drags_household_probability=drags_household_probability,
        )
        self.link_households_and_carehomes(super_areas)

    @classmethod
    def from_config(cls, super_areas: SuperAreas, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(super_areas, **config)

    def link_households_and_carehomes(self, super_areas):
        for super_area in super_areas:
            households_super_area = []
            for area in super_area.areas:
                households_super_area += [household for household in area.households if household.type in ["families", "ya_parents", "nokids"]]
                np.random.shuffle(households_super_area)
            for area in super_areas.areas:
                if area.carehome is not None:
                    carehome_residents = area.carehome[area.carehome.SubgroupType.residents].people 
                    for i, _ in enumerate(carehome_residents):
                        if households_super_area[i].associated_households is None:
                            households_super_area[i].associated_households = [area.carehome[area.carehome.SubgroupType.visitors]]
                        else:
                            households_super_area[i].associated_households.append(area.carehome[area.carehome.SubgroupType.visitors])


