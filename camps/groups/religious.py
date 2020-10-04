import numpy as np
import pandas as pd
import yaml
from typing import List, Optional
from june.geography import Areas

from june.groups.leisure.social_venue import SocialVenue, SocialVenues, SocialVenueError
from june.groups.leisure.social_venue_distributor import SocialVenueDistributor
from camps.paths import camp_data_path, camp_configs_path

default_religiouss_coordinates_filename = camp_data_path / "input/activities/religious.csv"
default_config_filename = camp_configs_path / "defaults/groups/religious.yaml"

class Religious(SocialVenue):
    max_size = np.inf


class Religiouss(SocialVenues):
    social_venue_class = Religious
    default_coordinates_filename = default_religiouss_coordinates_filename


class ReligiousDistributor(SocialVenueDistributor):
    default_config_filename = default_config_filename
