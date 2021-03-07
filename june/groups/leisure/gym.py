from .social_venue import SocialVenue, SocialVenues
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path

default_gym_coordinates_filename = data_path / "input/leisure/gyms_per_super_area.csv"
default_config_filename = configs_path / "defaults/groups/leisure/gyms.yaml"


class Gym(SocialVenue):
    max_size = 300
    pass

class Gyms(SocialVenues):
    social_venue_class = Gym
    default_coordinates_filename = default_gym_coordinates_filename

class GymDistributor(SocialVenueDistributor):
    default_config_filename = default_config_filename

