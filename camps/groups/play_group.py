import numpy as np
import pandas as pd
import yaml
from typing import List, Optional, Dict
from enum import IntEnum

from june.groups.group import Group, Supergroup
from june.geography import Area
from june.groups.leisure.social_venue import SocialVenue, SocialVenues, SocialVenueError
from june.groups.leisure.social_venue_distributor import SocialVenueDistributor
from camps.paths import camp_data_path, camp_configs_path
from camps.geography import CampArea

default_config_filename = camp_configs_path / "defaults/groups/play_group.yaml"

class PlayGroup(SocialVenue):
    class SubgroupType(IntEnum):
        young = 0
        mid = 1
        old = 2

    def __init__(
        self, age_group_limits: List[int] = [3, 7, 12, 17], max_size: int = 10, area = None
    ):
        super().__init__()
        self.age_group_limits = age_group_limits
        self.min_age = age_group_limits[0]
        self.max_age = age_group_limits[-1]-1
        self.max_size = max_size
        self.area = area

    @property
    def coordinates(self):
        return self.area.coordinates

    def get_leisure_subgroup(self, person: "Person"):
        if person.age >= self.min_age and person.age <= self.max_age:
            subgroup_idx = (
                np.searchsorted(self.age_group_limits, person.age, side="right") - 1
            )
            return self.subgroups[subgroup_idx]
        else:
            return


class PlayGroups(SocialVenues):
    def __init__(self, play_groups: List[PlayGroup]):
        super().__init__(play_groups, make_tree=False)

    @classmethod
    def for_areas(
        cls,
        areas: List[CampArea],
        venues_per_capita: float = 1 / 20,
        age_group_limits: List[int] = [3, 7, 12, 16],
        max_size: int = 10,
    ):
        play_groups = []
        for area in areas:
            area_population = len(
                [
                    person
                    for person in area.people
                    if person.age >= age_group_limits[0]
                    and person.age <= age_group_limits[-1]
                ]
            )
            for _ in range(0, int(np.ceil(venues_per_capita * area_population))):
                play_group = PlayGroup(
                    age_group_limits=age_group_limits, max_size=max_size, area=area
                )
                area.play_groups.append(play_group)
                play_groups.append(play_group)
        return cls(play_groups=play_groups)


class PlayGroupDistributor(SocialVenueDistributor):
    def __init__(
            self,
            play_groups: PlayGroups,
            male_age_probabilities: Optional[Dict] = None,
            female_age_probabilities: Optional[Dict] = None,
            weekend_boost: float = 1.,
            drags_household_probability = 0.
        ):
        super().__init__(
            social_venues=play_groups,
            male_age_probabilities=male_age_probabilities,
            female_age_probabilities=female_age_probabilities,
            weekend_boost=weekend_boost,
            drags_household_probability=drags_household_probability
        )

    @classmethod
    def from_config(cls, play_groups, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(play_groups, **config)

    def get_social_venue_for_person(self, person):
        """
        We select a random play group from the person area.
        """
        venue = np.random.choice(person.area.play_groups)
        return venue

    def get_possible_venues_for_area(self, area: Area):
        if area.play_groups:
            venue = np.random.choice(area.play_groups)
            return [venue]
        else:
            return None
