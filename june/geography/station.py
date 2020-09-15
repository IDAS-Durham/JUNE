from typing import List
import pandas as pd
import numpy as np

from june.paths import data_path
from june.geography import City, Areas

default_stations_filename = (
    data_path / "input/geography/england_wales_main_stations.csv"
)


class Station:
    """
    A train station. This is used to model commute and travel.
    """

    def __init__(self, name: str = None, area: str = None, city: City = None):
        self.name = name
        self.area = area
        self.city = city

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
        stations.set_index("area", inplace=True)
        stations = stations.loc[areas]
        stations.reset_index(inplace=True)
        station_instances = []
        for _, row in stations.iterrows():
            station = Station(name=row["station"], area=row["area"])
            station_instances.append(station)
        return cls(station_instances)

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
        for station in stations:
            station.city = city
        return stations


class StationHub:
    """
    A station hub is a hub located at a certain distance from a station that gathers commuters around its location
    """

    def __init__(self, station: str = None, city: str = None, area: str = None):
        self.station = station
        self.city = city
        self.area = area


class StationHubs:
    """
    A collection of hubs belonging to one station.
    """

    def __init__(self, station_hubs: List[StationHub]):
        self.members = station_hubs

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
        distance_to_station: int = 7,
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
        station_coordinates = np.array(station.get_coordinates(areas=areas))
        for i in range(number_of_hubs):
            hub_position = station_coordinates + np.array(
                [
                    distance_to_station * np.cos(angle),
                    distance_to_station * np.sin(angle),
                ]
            )
            print(hub_position)
            angle += delta_angle
            area = areas.get_closest_area(np.array(hub_position))
            hub = StationHub(station=station.name, city=station.city, area=area.name)
            hubs.append(hub)

        return cls(hubs)
