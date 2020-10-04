import numpy as np
import pandas as pd
import yaml
from typing import List, Optional
from june.geography import Areas

from june.groups.leisure.social_venue import SocialVenue, SocialVenues, SocialVenueError
from june.groups.leisure.social_venue_distributor import SocialVenueDistributor
from camps.paths import camp_data_path, camp_configs_path

default_female_communals_coordinates_filename = camp_data_path / "input/activities/female_communal.csv"
default_config_filename = camp_configs_path / "defaults/groups/female_communal.yaml"

class FemaleCommunal(SocialVenue):
    max_size = np.inf

class FemaleCommunals(SocialVenues):
    social_venue_class = FemaleCommunal
    default_coordinates_filename = default_female_communals_coordinates_filename


class FemaleCommunalDistributor(SocialVenueDistributor):
    default_config_filename = default_config_filename
