from typing import List
import pandas as pd
import numpy as np
import math
import logging
from random import randint
from sklearn.neighbors import BallTree
from itertools import chain, count
from collections import defaultdict

from june.paths import data_path, configs_path
from june.geography import City, SuperAreas, SuperArea
from june.groups import Supergroup, ExternalGroup, ExternalSubgroup
from june.utils.distances import add_distance_to_lat_lon

default_super_stations_filename = (
    data_path / "input/geography/stations_per_super_area_ew.csv"
)

logger = logging.getLogger(__name__)

class Station:
    """
    This represents a general station.
    """

    external = False
    _id = count()

    def __init__(self, city: str = None, super_area: SuperArea = None):
        self.id = next(self._id)
        self.commuter_ids = set()
        self.city = city
        self.super_area = super_area

    @property
    def coordinates(self):
        return self.super_area.coordinates


class CityStation(Station):
    """
    This is a city station for internal commuting
    """

    def __init__(self, city: str = None, super_area: SuperArea = None):
        super().__init__(city=city, super_area=super_area)
        self.city_transports = []

    @property
    def n_city_transports(self):
        return len(self.city_transports)

    def get_commute_subgroup(self):
        return self.city_transports[randint(0, self.n_city_transports - 1)][0]

    @property
    def station_type(self):
        return "city"


class InterCityStation(Station):
    """
    This is an inter-city station for inter-city commuting
    """

    def __init__(self, city: str = None, super_area: SuperArea = None):
        super().__init__(city=city, super_area=super_area)
        self.inter_city_transports = []

    @property
    def n_inter_city_transports(self):
        return len(self.inter_city_transports)

    def get_commute_subgroup(self):
        return self.inter_city_transports[randint(0, self.n_inter_city_transports - 1)][
            0
        ]

    @property
    def station_type(self):
        return "inter_city"


class Stations(Supergroup):
    """
    A collection of stations belonging to a city.
    """

    def __init__(self, stations: List[Station]):
        super().__init__(stations)
        self._ball_tree = None

    @classmethod
    def from_city_center(
        cls,
        city: City,
        type: str,
        super_areas: SuperAreas,
        number_of_stations: int = 4,
        distance_to_city_center: int = 20,
    ):
        """
        Initialises ``number_of_stations`` radially around the city center.

        Parameters
        ----------
        super_areas 
            The super_areas where to put the hubs on
        number_of_stations:
            How many stations to initialise
        distance_to_city_center 
            The distance from the center to the each station 
        """
        stations = []
        angle = 0
        delta_angle = 2 * np.pi / number_of_stations
        x = distance_to_city_center
        y = 0
        city_coordinates = city.coordinates
        for i in range(number_of_stations):
            station_position = add_distance_to_lat_lon(
                city_coordinates[0],
                city_coordinates[1],
                x=x,
                y=y
            )
            angle += delta_angle
            x = distance_to_city_center * np.cos(angle)
            y = distance_to_city_center * np.sin(angle)
            super_area = super_areas.get_closest_super_area(np.array(station_position))
            if type == "city_station":
                station = CityStation(city=city.name, super_area=super_area,)
            elif type == "inter_city_station":
                station = InterCityStation(city=city.name, super_area=super_area,)
            else:
                raise ValueError
            stations.append(station)
        return cls(stations)

    def _construct_ball_tree(self):
        coordinates = np.array([np.deg2rad(station.coordinates) for station in self])
        self._ball_tree = BallTree(coordinates, metric="haversine")

    def get_closest_station(self, coordinates):
        coordinates = np.array(coordinates)
        if self._ball_tree is None:
            raise ValueError("Stations initialized without a BallTree")
        if coordinates.shape == (2,):
            coordinates = coordinates.reshape(1, -1)
        indcs = self._ball_tree.query(
            np.deg2rad(coordinates), return_distance=False, k=1
        )
        super_areas = [self[idx] for idx in indcs[:, 0]]
        return super_areas[0]


class ExternalStation(ExternalGroup):
    external = True

    def __init__(self, id: int, domain_id: int, city: str = None):
        super().__init__(spec="station", domain_id=domain_id, id=id)
        self.commuter_ids = set()
        self.city = city

    @property
    def coordinates(self):
        return self.super_area.coordinates

    def get_commute_subgroup(self):
        raise NotImplementedError


class ExternalCityStation(ExternalStation):
    """
    This an external city station that lives outside the simulated domain.
    """

    def __init__(self, id: int, domain_id: int, city: str = None):
        super().__init__(id=id, domain_id=domain_id, city=city)
        self.city_transports = []

    @property
    def n_city_transports(self):
        return len(self.city_transports)

    def get_commute_subgroup(self):
        group = self.city_transports[randint(0, self.n_city_transports - 1)]
        return ExternalSubgroup(group=group, subgroup_type=0)


class ExternalInterCityStation(ExternalStation):
    """
    This an external city station that lives outside the simulated domain.
    """

    def __init__(self, id: int, domain_id: int, city: str = None):
        super().__init__(id=id, domain_id=domain_id, city=city)
        self.inter_city_transports = []

    @property
    def n_inter_city_transports(self):
        return len(self.inter_city_transports)

    def get_commute_subgroup(self):
        group = self.inter_city_transports[randint(0, self.n_inter_city_transports - 1)]
        return ExternalSubgroup(group=group, subgroup_type=0)
