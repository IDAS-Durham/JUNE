import numpy as np
import pandas as pd

from .social_venue import SocialVenue, SocialVenues
from june.paths import data_path

default_pub_coordinates_filename = (
    data_path / "geographical_data/pubs_uk24727_latlong.txt"
)


class Pub(SocialVenue):
    """
    Pubs are fun.
    """

    def __init__(self):
        super().__init__()


class Pubs(SocialVenues):
    def __init__(self):
        super().__init__()


    @classmethod
    def from_file(cls, coordinates_filename: str = default_pub_coordinates_filename):
        pub_coordinates = np.loadtxt(coordinates_filename)
        return cls.from_coordinates(pub_coordinates)


