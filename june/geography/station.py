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

default_super_stations_filename = (
    data_path / "input/geography/stations_per_super_area_ew.csv"
)

earth_radius = 6371  # km

logger = logging.getLogger(__name__)

def _haversine_distance(origin, destination):
    """
    Taken from https://gist.github.com/rochacbruno/2883505
    """
    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = 6371  # km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(
        math.radians(lat1)
    ) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c
    return d


def _add_distance_to_lat_lon(latitude, longitude, distance, bearing):
    """
    Given a latitude and a longitude (in degrees), a distance (IN KM), and a bearing (IN RADIANS),
    returns the new latitude and longitude (in degrees) given by the displacement.

    Taken from https://stackoverflow.com/questions/7222382/get-lat-long-given-current-point-distance-and-bearing
    """
    lat1 = math.radians(latitude)  # Current lat point converted to radians
    lon1 = math.radians(longitude)  # Current long point converted to radians

    lat2 = math.asin(
        math.sin(lat1) * math.cos(distance / earth_radius)
        + math.cos(lat1) * math.sin(distance / earth_radius) * math.cos(bearing)
    )

    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(distance / earth_radius) * math.cos(lat1),
        math.cos(distance / earth_radius) - math.sin(lat1) * math.sin(lat2),
    )

    lat2 = math.degrees(lat2)
    lon2 = math.degrees(lon2)
    return lat2, lon2



class Station:
    """
    This represents a railway station (like King's Cross).
    """
    external = False
    _id = count()

    def __init__(
        self, city: str = None, super_area: SuperArea = None
    ):
        self.id = next(self._id)
        self.commuter_ids = set()
        self.city = city
        self.super_area = super_area
        self.inter_city_transports = []

    @property
    def coordinates(self):
        return self.super_area.coordinates

    def get_commute_subgroup(self, person):
        return self.inter_city_transports[
            randint(0, len(self.inter_city_transports) - 1)
        ][0]


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
        city_coordinates = city.coordinates
        for i in range(number_of_stations):
            station_position = _add_distance_to_lat_lon(
                city_coordinates[0],
                city_coordinates[1],
                distance_to_city_center,
                angle,
            )
            angle += delta_angle
            super_area = super_areas.get_closest_super_area(np.array(station_position))
            station = Station(
                city=city.name,
                super_area=super_area,
            )
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
    """
    This a station that lives outside the simulated domain.
    """
    __slots__ = "commuter_ids", "inter_city_transports", "super_area"
    external = True
    def __init__(self, id, domain_id, commuter_ids = None):
        super().__init__(spec="station", domain_id=domain_id, id=id)
        self.commuter_ids = commuter_ids
        self.inter_city_transports = None
        self.super_area = None

    def get_commute_subgroup(self, person):
        group = self.inter_city_transports[
            randint(0, len(self.inter_city_transports) - 1)
        ]
        return ExternalSubgroup(group=group, subgroup_type=0)
