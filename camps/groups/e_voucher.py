import numpy as np
import pandas as pd
import yaml
from typing import List, Optional
from june.geography import Areas

from june.groups.leisure.social_venue import SocialVenue, SocialVenues, SocialVenueError
from june.groups.leisure.social_venue_distributor import SocialVenueDistributor
from camps.paths import camp_data_path, camp_configs_path

default_evouchers_coordinates_filename = camp_data_path / "input/activities/e_voucher_outlet.csv"
default_config_filename = camp_configs_path / "defaults/groups/e_voucher_outlet.yaml"

class EVoucher(SocialVenue):
    max_size = np.inf

class EVouchers(SocialVenues):
    social_venue_class = EVoucher
    default_coordinates_filename = default_evouchers_coordinates_filename

class EVoucherDistributor(SocialVenueDistributor):
    default_config_filename = default_config_filename
