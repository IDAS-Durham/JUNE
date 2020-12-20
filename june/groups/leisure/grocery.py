from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path

default_config_filename = configs_path / "defaults/groups/leisure/groceries.yaml"
default_groceries_coordinates_filename = (
    data_path / "input/leisure/groceries_per_super_area.csv"
)


class Grocery(SocialVenue):
    max_size = 200


class Groceries(SocialVenues):
    social_venue_class = Grocery
    default_coordinates_filename = default_groceries_coordinates_filename


class GroceryDistributor(SocialVenueDistributor):
    default_config_filename = default_config_filename
