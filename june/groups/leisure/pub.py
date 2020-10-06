import numpy as np
import pandas as pd
import yaml
from typing import List

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path
from june.geography import Geography
from june.geography import Area, Areas, SuperArea, SuperAreas

default_pub_coordinates_filename = data_path / "input/leisure/pubs_per_super_area.csv"
default_config_filename = configs_path / "defaults/groups/leisure/pubs.yaml"


class Pub(SocialVenue):
    max_size = 100
    pass

class Pubs(SocialVenues):
    social_venue_class = Pub
    default_coordinates_filename = default_pub_coordinates_filename

class PubDistributor(SocialVenueDistributor):
    default_config_filename = default_config_filename

