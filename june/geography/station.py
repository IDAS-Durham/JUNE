from typing import List
import pandas as pd
import numpy as np
import math
from sklearn.neighbors import BallTree

from june.paths import data_path
from june.geography import City, Areas, Area

default_stations_filename = (
    data_path / "input/geography/england_wales_main_stations.csv"
)

earth_radius = 6371  # km


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
    A train station. This is used to model commute and travel.
    """

    def __init__(self, name: str = None, area: str = None, city: City = None):
        self.name = name
        self.area = area
        self.city = city
        self.hubs = None

    def get_coordinates(self, areas: Areas):
        return areas.members_by_name[self.area].coordinates


class Stations:
    """
    A collection of stations, probably in the same city.
    """

    def __init__(self, stations: List[Station]):
        self.members = stations

    def __iter__(self):
        return iter(self.members)

    def __getitem__(self, idx):
        return self.members[idx]

    @classmethod
    def from_file(
        cls, areas: List[str], station_areas_filename=default_stations_filename
    ):
        """
        Filters stations in the given file with the given areas list.
        
        Parameters
        ----------
        areas
            A list of area names. 
        station_areas_filename
            A path to a csv file containing two columns, "station" and "area", mapping each station to an area.
        """
        stations = pd.read_csv(station_areas_filename)
        stations = stations.loc[stations.area.isin(areas)]
        if len(stations) > 0:
            stations.reset_index(inplace=True)
            station_instances = []
            for _, row in stations.iterrows():
                station = Station(name=row["station"], area=row["area"])
                station_instances.append(station)
            return cls(station_instances)
        else:
            return None

    @classmethod
    def for_city(cls, city: City, station_areas_filename=default_stations_filename):
        """
        Initializes stations for the given city.

        Parameters
        ----------
        city
            An instance of a City
        station_areas_filename
            A path to a csv file containing two columns, "station" and "area", mapping each station to an area.
        """
        stations = cls.from_file(
            areas=city.areas, station_areas_filename=station_areas_filename
        )
        if stations:
            for station in stations:
                station.city = city
        return stations


class StationHub:
    """
    A station hub is a hub located at a certain distance from a station that gathers commuters around its location
    """

    def __init__(self, station: str = None, city: str = None, area: Area = None):
        self.station = station
        self.city = city
        self.area = area

    @property
    def coordinates(self):
        return self.area.coordinates


class StationHubs:
    """
    A collection of hubs belonging to one station.
    """

    def __init__(self, station_hubs: List[StationHub], ball_tree = True):
        self.members = station_hubs
        self._ball_tree = None
        if ball_tree:
            self._ball_tree = self._construct_ball_tree()

    def __iter__(self):
        return iter(self.members)

    def __getitem__(self, idx):
        return self.members[idx]

    def __len__(self):
        return len(self.members)

    @classmethod
    def for_station(
        cls,
        areas: Areas,
        station: Station = None,
        number_of_hubs: int = 4,
        distance_to_station: int = 20,
    ):
        """
        Distributes hubs (``number_of_hubs``) around the ``city``. The hubs are uniformly distributed in a circle around
        the station location, at a distance ``distance_to_location``.
        The ``areas`` argument needs to be passed, to know where to locate the hub.

        Parameters
        ----------
        areas 
            The areas where to put the hubs on
        station
            The station the hub belongs to
        number_of_hubs:
            How many hubs to initialise
        distance_to_station
            The distance from the station to the hubs
        """
        hubs = []
        angle = 0
        delta_angle = 2 * np.pi / number_of_hubs
        station_coordinates = station.get_coordinates(areas=areas)
        for i in range(number_of_hubs):
            hub_position = _add_distance_to_lat_lon(
                station_coordinates[0],
                station_coordinates[1],
                distance_to_station,
                angle,
            )
            angle += delta_angle
            area = areas.get_closest_area(np.array(hub_position))
            hub = StationHub(station=station.name, city=station.city, area=area)
            hubs.append(hub)

        return cls(hubs)

    def _construct_ball_tree(self):
        coordinates = np.array([np.deg2rad(hub.coordinates) for hub in self])
        ball_tree = BallTree(coordinates, metric = 'haversine')
        return ball_tree

    def get_closest_hub(self, coordinates):
        coordinates = np.array(coordinates)
        if self._ball_tree is None:
            raise ValueError("Hubs initialized without a BallTree")
        if coordinates.shape == (2,):
            coordinates = coordinates.reshape(1, -1)
        indcs = self._ball_tree.query(
            np.deg2rad(coordinates), return_distance=False, k=1
        )
        areas = [self[idx] for idx in indcs[:, 0]]
        return areas[0]
