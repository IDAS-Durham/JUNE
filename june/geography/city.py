import pandas as pd
from typing import List
import numpy as np
from random import randint
from sklearn.neighbors import BallTree
from itertools import chain, count
from collections import defaultdict
import logging

from june.paths import data_path
from june.geography import SuperArea, Geography
from june.groups import Supergroup, ExternalSubgroup, ExternalGroup

default_cities_filename = data_path / "input/geography/cities_per_super_area_ew.csv"

earth_radius = 6371  # km

logger = logging.getLogger(__name__)


def _calculate_centroid(latitudes, longitudes):
    """
    Calculates the centroid of the city.
    WARNING: This currently takes the mean of the latitude and longitude, however this is not correct for some cases,
    eg, the mean angle between 1 and 359 should be 0, not 180, etc.
    """
    return [np.mean(latitudes), np.mean(longitudes)]


class City:
    """
    A city is a collection of areas, with some added methods for functionality,
    such as commuting or local lockdowns.
    """
    external = False

    _id = count()

    def __init__(
        self,
        super_areas: List[str] = None,
        super_area: SuperArea = None,
        name: str = None,
        coordinates=None,
    ):
        """
        Initializes a city. A city is defined by a collection of ``super_areas`` and is located at one particular ``super_area``.
        The location to one ``super_area`` is necessary for domain parallelisation.

        Parameters
        ----------
        super_areas:
            A list of super area names
        super_area:
            The ``SuperArea`` instance of where the city resides
        name
            The city name
        coordinates
            A tuple or array of floats indicating latitude and longitude of the city (in degrees).
        """
        self.id = next(self._id)
        self.super_area = super_area
        self.super_areas = super_areas
        self.name = name
        self.super_stations = None
        self.stations = None
        self.coordinates = coordinates
        self.city_transports = []
        self.commuter_ids = set()  # internal commuters in the city

    @classmethod
    def from_file(cls, name, city_super_areas_filename=default_cities_filename):
        city_super_areas_df = pd.read_csv(city_super_areas_filename)
        city_super_areas_df.set_index("city", inplace=True)
        return cls.from_df(name=name, city_super_areas_df=city_super_areas_df)

    @classmethod
    def from_df(cls, name, city_super_areas_df):
        city_super_areas = city_super_areas_df.loc[name].values
        return cls(super_areas=city_super_areas, name=name)

    def get_commute_subgroup(self, person):
        """
        Gets the commute subgroup of the person.
        """
        if person.id in self.commuter_ids:
            return self.city_transports[randint(0, len(self.city_transports) - 1)][0]
        else:
            closest_station = person.super_area.closest_station
            return closest_station.get_commute_subgroup(person)


class Cities(Supergroup):
    """
    A collection of cities.
    """

    def __init__(self, cities: List[City], ball_tree=True):
        super().__init__(cities)
        if ball_tree:
            self._ball_tree = self._construct_ball_tree()

    @classmethod
    def for_super_areas(
        cls,
        super_areas: List[SuperArea],
        city_super_areas_filename=default_cities_filename,
    ):
        """
        Initializes the cities which are on the given super areas.
        """
        city_super_areas = pd.read_csv(city_super_areas_filename)
        city_super_areas = city_super_areas.loc[
            city_super_areas.super_area.isin(
                [super_area.name for super_area in super_areas]
            )
        ]
        city_super_areas.reset_index(inplace=True)
        city_super_areas.set_index("city", inplace=True)
        cities = []
        for city in city_super_areas.index.unique():
            super_area_names = city_super_areas.loc[city, "super_area"]
            if type(super_area_names) == str:
                super_area_names = [super_area_names]
            city = City(name=city, super_areas=super_area_names)
            lats = []
            lons = []
            for super_area_name in super_area_names:
                super_area = super_areas.members_by_name[super_area_name]
                super_area.city = city
                lats.append(super_area.coordinates[0])
                lons.append(super_area.coordinates[1])
            city.coordinates = _calculate_centroid(lats, lons)
            city.super_area = super_areas.get_closest_super_area(city.coordinates)
            cities.append(city)
        return cls(cities)

    @classmethod
    def for_geography(
        cls, geography: Geography, city_super_areas_filename=default_cities_filename
    ):
        return cls.for_super_areas(
            super_areas=geography.super_areas,
            city_super_areas_filename=city_super_areas_filename,
        )

    def _construct_ball_tree(self):
        """
        Constructs a NN tree with the haversine metric for the cities.
        """
        coordinates = np.array([np.deg2rad(city.coordinates) for city in self])
        ball_tree = BallTree(coordinates, metric="haversine")
        return ball_tree

    def get_closest_cities(self, coordinates, k=1, return_distance=False):
        coordinates = np.array(coordinates)
        if self._ball_tree is None:
            raise ValueError("Cities initialized without a BallTree")
        if coordinates.shape == (2,):
            coordinates = coordinates.reshape(1, -1)
        if return_distance:
            distances, indcs = self.ball_tree.query(
                np.deg2rad(coordinates), return_distance=return_distance, k=k
            )
            if coordinates.shape == (1, 2):
                cities = [self[idx] for idx in indcs[0]]
                return cities, distances[0] * earth_radius
            else:
                cities = [self[idx] for idx in indcs[:, 0]]
                return cities, distances[:, 0] * earth_radius
        else:
            indcs = self._ball_tree.query(
                np.deg2rad(coordinates), return_distance=return_distance, k=k
            )
            cities = [self[idx] for idx in indcs[0]]
            return cities

    def get_closest_city(self, coordinates):
        return self.get_closest_cities(coordinates, k=1, return_distance=False)[0]

    def get_closest_commuting_city(self, coordinates):
        cities_by_distance = self.get_closest_cities(coordinates, k=len(self.members))
        for city in cities_by_distance:
            if city.stations.members:
                return city
        logger.warning("No commuting city in this world.")

class ExternalCity(ExternalGroup):
    """
    This a city that lives outside the simulated domain.
    """
    __slots__ = "commuter_ids", "city_transports", "super_area", "coordinates"
    external = True
    def __init__(self, id, domain_id, coordinates= None, commuter_ids = None):
        super().__init__(spec="city", domain_id=domain_id, id=id)
        self.commuter_ids = commuter_ids
        self.city_transports = None
        self.super_area = None
        self.coordinates = coordinates

    def get_commute_subgroup(self, person):
        group = self.city_transports[
            randint(0, len(self.inter_city_transports) - 1)
        ]
        return ExternalSubgroup(group=group, subgroup_type=0)
