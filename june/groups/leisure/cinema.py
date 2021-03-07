from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path

default_cinemas_coordinates_filename = (
    data_path / "input/leisure/cinemas_per_super_area.csv"
)
default_config_filename = configs_path / "defaults/groups/leisure/cinemas.yaml"


class Cinema(SocialVenue):
    max_size = 1000


class Cinemas(SocialVenues):
    social_venue_class = Cinema
    default_coordinates_filename = default_cinemas_coordinates_filename


class CinemaDistributor(SocialVenueDistributor):
    default_config_filename = default_config_filename
