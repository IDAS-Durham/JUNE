import numpy as np
import pandas as pd
import yaml
from typing import List, Optional
from enum import IntEnum

from june.groups.group import Group, Supergroup
from june.groups.leisure.social_venue import SocialVenue, SocialVenues, SocialVenueError
from june.groups.leisure.social_venue_distributor import SocialVenueDistributor
from camps.paths import camp_data_path, camp_configs_path


class PlayGroup(Group):
    class SubgroupType(IntEnum):
        young = 0
        mid = 1
        old = 2

    def __init__(self, age_groups_limits=[3,7,12,16]):
        super().__init__()
        self.min_age = age_groups_limits[0]
        self.max_age = age_groups_limits[-1] 
        self.age_groups_limits = age_groups_limits

    def get_leisure_subgroup(self, person):
        if person.age >= self.min_age and person.age <= self.max_age:
            subgroup_idx = (
                np.searchsorted(
                    self.age_groups_limits, person.age, side="right"
                )
                - 1
            )
            return self.subgroups[subgroup_idx]
        else:
            return
