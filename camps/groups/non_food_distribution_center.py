import numpy as np
import pandas as pd
import yaml
from typing import List, Optional
from june.geography import Areas

from june.groups.leisure.social_venue import SocialVenue, SocialVenues, SocialVenueError
from june.groups.leisure.social_venue_distributor import SocialVenueDistributor
from camps.paths import camp_data_path, camp_configs_path

default_nfdistributioncenters_coordinates_filename = (
    camp_data_path / "input/activities/non_food_distribution_center.csv"
)
default_config_filename = (
    camp_configs_path / "defaults/groups/non_food_distribution_center.yaml"
)


class NFDistributionCenter(SocialVenue):
    max_size = np.inf


class NFDistributionCenters(SocialVenues):
    social_venue_class = NFDistributionCenter
    default_coordinates_filename = default_nfdistributioncenters_coordinates_filename


class NFDistributionCenterDistributor(SocialVenueDistributor):
    default_config_filename = default_config_filename
