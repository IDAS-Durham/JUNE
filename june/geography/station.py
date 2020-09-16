from typing import List
import pandas as pd
import numpy as np
import math
import logging
from sklearn.neighbors import BallTree
from itertools import chain, count
from collections import defaultdict

from june.paths import data_path
from june.geography import City, SuperAreas, SuperArea

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


class SuperStation:
    """
    An important train station (like King's Cross). This is used to model commute and travel.
    """

    _id = count()

    def __init__(self, name: str = None, super_area: str = None, city: str = None):
        self.id = next(self._id)
        self.name = name
        self.super_area = super_area
        self.city = city
        self.stations = None

    def get_coordinates(self, super_areas: SuperAreas):
        return super_areas.members_by_name[self.super_area].coordinates

    @property
    def commuters(self):
        return list(chain.from_iterable(station.commuters for station in self.stations))


class SuperStations:
    """
    A collection of super stations, probably in the same city.
    """

    def __init__(self, stations: List[SuperStation]):
        self.members = stations

    def __iter__(self):
        return iter(self.members)

    def __getitem__(self, idx):
        return self.members[idx]

    def __len__(self):
        return len(self.members)

    @classmethod
    def from_file(
        cls,
        super_areas: List[str],
        city: str = None,
        super_station_super_areas_filename=default_super_stations_filename,
    ):
        """
        Filters stations in the given file with the given super_areas list.
        
        Parameters
        ----------
        super_areas
            A list of super_area names. 
        station_super_areas_filename
            A path to a csv file containing two columns, "station" and "super_area", mapping each station to an super_area.
        """
        stations = pd.read_csv(super_station_super_areas_filename)
        stations = stations.loc[stations.super_area.isin(super_areas)]
        if len(stations) > 0:
            stations.reset_index(inplace=True)
            station_instances = []
            for _, row in stations.iterrows():
                station_name = row["station"]
                logger.info(f"Station {station_name} initialised.")
                station = SuperStation(
                    name=station_name, super_area=row["super_area"], city=city
                )
                station_instances.append(station)
            return cls(station_instances)
        else:
            return cls([])

    @classmethod
    def for_city(
        cls,
        city: City,
        super_station_super_areas_filename=default_super_stations_filename,
    ):
        """
        Initializes stations for the given city.

        Parameters
        ----------
        city
            An instance of a City
        station_super_areas_filename
            A path to a csv file containing two columns, "station" and "super_area", mapping each station to an super_area.
        """
        super_stations = cls.from_file(
            super_areas=city.super_areas,
            city=city.name,
            super_station_super_areas_filename=super_station_super_areas_filename,
        )
        return super_stations


class Station:
    """
    This represents smaller stations (like your nearest bus station) that go to one
    SuperStation.
    """

    _id = count()

    def __init__(
        self, super_station: str = None, city: str = None, super_area: SuperArea = None
    ):
        self.id = next(self._id)
        self.super_station = super_station
        self.commuters = []
        self.city = city
        self.super_area = super_area
        self.inter_city_transports = []

    @property
    def coordinates(self):
        return self.super_area.coordinates


class Stations:
    """
    A collection of stations belonging to one super station.
    """

    def __init__(self, stations: List[Station]):
        self.members = stations
        self._ball_tree = None

    def __iter__(self):
        return iter(self.members)

    def __getitem__(self, idx):
        return self.members[idx]

    def __len__(self):
        return len(self.members)

    def __add__(self, stations: "Stations"):
        self.members += stations.members
        return self

    @classmethod
    def for_super_station(
        cls,
        super_areas: SuperAreas,
        super_station: SuperStation = None,
        number_of_stations: int = 4,
        distance_to_super_station: int = 20,
    ):
        """
        Distributes stations (``number_of_stations``) around the ``super_station``. The stations are uniformly distributed in a circle around
        the super station location, at a distance ``distance_to_super_station``.
        The ``super_areas`` argument needs to be passed, to know where to locate the station.

        Parameters
        ----------
        super_areas 
            The super_areas where to put the hubs on
        super_station
            The super station the station belongs to
        number_of_stations:
            How many stations to initialise
        distance_to_station
            The distance from the station to the super station 
        """
        stations = []
        angle = 0
        delta_angle = 2 * np.pi / number_of_stations
        station_coordinates = super_station.get_coordinates(super_areas=super_areas)
        for i in range(number_of_stations):
            station_position = _add_distance_to_lat_lon(
                station_coordinates[0],
                station_coordinates[1],
                distance_to_super_station,
                angle,
            )
            angle += delta_angle
            super_area = super_areas.get_closest_super_area(np.array(station_position))
            station = Station(
                super_station=super_station.name,
                city=super_station.city,
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
