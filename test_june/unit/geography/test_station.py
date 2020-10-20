from pathlib import Path
import numpy as np

from june.geography import SuperArea, SuperAreas, Station, Stations, City, Cities
from june.geography.station import CityStation, InterCityStation

super_stations_test_file = Path(__file__).parent / "stations.csv"


class TestStations:
    def test__stations_setup(self):
        station = Station(city="Barcelona", super_area=SuperArea(name="b1"))
        assert station.city == "Barcelona"
        assert station.super_area.name == "b1"

    def test__stations_for_city_center(self):
        super_areas = SuperAreas(
            [
                SuperArea(name="b1", coordinates=[0, 0]),
                SuperArea(name="b2", coordinates=[1, 0]),
                SuperArea(name="b3", coordinates=[0, 1]),
                SuperArea(name="b4", coordinates=[-1, 0]),
                SuperArea(name="b5", coordinates=[0, -1]),
            ],
            ball_tree=True,
        )
        city = City(name="Barcelona", coordinates=[0, 0], super_area=super_areas[0])
        city_stations = Stations.from_city_center(
            city=city,
            number_of_stations=4,
            distance_to_city_center=500,
            super_areas=super_areas,
            type="city_station"
        )
        assert len(city_stations) == 4
        for st in city_stations:
            assert isinstance(st, CityStation)
        station_super_areas = []
        for station in city_stations:
            station_super_areas.append(station.super_area.name)
            assert station.city == "Barcelona"
            assert station.super_area.name in ["b1", "b2", "b3", "b4", "b5"]
        assert len(np.unique(station_super_areas)) == 4
        city_stations._construct_ball_tree()
        station = city_stations.get_closest_station([0.1, 0])
        assert station.coordinates[0] == 1
        assert station.coordinates[1] == 0
        station = city_stations.get_closest_station([-50, -10])
        assert station.coordinates[0] == -1
        assert station.coordinates[1] == 0
        inter_city_stations = Stations.from_city_center(
            city=city,
            number_of_stations=4,
            distance_to_city_center=500,
            super_areas=super_areas,
            type="inter_city_station"
        )
        for st in inter_city_stations:
            assert isinstance(st, InterCityStation)
