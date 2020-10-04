import numpy as np
import pandas as pd
import yaml
from typing import List, Optional
from june.geography import Areas

from june.groups.leisure.social_venue import SocialVenue, SocialVenues, SocialVenueError
from june.groups.leisure.social_venue_distributor import SocialVenueDistributor
from camps.paths import camp_data_path, camp_configs_path

default_distribution_centers_coordinates_filename = (
    camp_data_path / "input/activities/distribution_center.csv"
)
default_config_filename = camp_configs_path / "defaults/groups/distribution_center.yaml"


class DistributionCenter(SocialVenue):
    max_size = np.inf


class DistributionCenters(SocialVenues):
    social_venue_class = DistributionCenter
    default_coordinates_filename = default_distribution_centers_coordinates_filename


class DistributionCenterDistributor(SocialVenueDistributor):
    default_config_filename = default_config_filename
