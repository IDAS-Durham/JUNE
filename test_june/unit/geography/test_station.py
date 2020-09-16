from pathlib import Path
import numpy as np

from june.geography import SuperArea, SuperAreas, Station, Stations, City, Cities
from june.geography import Station, Stations, SuperStations, SuperStation 

super_stations_test_file = Path(__file__).parent / "stations.csv"

class TestSuperStations:
    def test__stations_setup(self):
        super_station = SuperStation(name="King's Cross", super_area="l1")
        assert super_station.super_area == "l1"
        assert super_station.name == "King's Cross"

    def test__super_stations_from_file(self):
        super_stations = SuperStations.from_file(
            super_areas=["l1", "l2"], super_station_super_areas_filename=super_stations_test_file
        )
        assert super_stations[0].super_area == "l1"
        assert super_stations[0].name == "King's Cross"
        assert super_stations[1].super_area == "l2"
        assert super_stations[1].name == "Victoria"

    def test__super_stations_for_city(self):
        city = City(name="London", super_areas=["l1", "l2"])
        super_stations = SuperStations.for_city(
            city=city, super_station_super_areas_filename=super_stations_test_file
        )
        assert super_stations[0].super_area == "l1"
        assert super_stations[0].name == "King's Cross"
        assert super_stations[1].super_area == "l2"
        assert super_stations[1].name == "Victoria"
        assert super_stations[0].city == city.name
        assert super_stations[1].city == city.name

    def test__super_station_coordinates(self):
        super_areas = SuperAreas(
            [SuperArea(name="c1", coordinates=[1, 2]), SuperArea(name="c2", coordinates=[3, 4])],
            ball_tree=False,
        )
        super_station = SuperStation(super_area="c1")
        assert super_station.get_coordinates(super_areas) == [1, 2]
        super_station = SuperStation(super_area="c2")
        assert super_station.get_coordinates(super_areas) == [3, 4]


class TestStations:
    def test__stations_setup(self):
        station = Station(super_station="Sants", city="Barcelona", super_area=SuperArea(name="b1"))
        assert station.super_station == "Sants"
        assert station.city == "Barcelona"
        assert station.super_area.name == "b1"

    def test__stations_for_super_station(self):
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
        super_station = SuperStation(name="Sants", super_area="b1")
        station_coordinates = super_station.get_coordinates(super_areas)
        assert station_coordinates == [0, 0]
        stations = Stations.for_super_station(
            super_station=super_station, number_of_stations=4, distance_to_super_station=500, super_areas = super_areas
        )
        assert len(stations) == 4
        station_super_areas = []
        for station in stations:
            station_super_areas.append(station.super_area.name)
            assert station.super_station == super_station.name
            assert station.city == station.city
            assert station.super_area.name in ["b1", "b2", "b3", "b4", "b5"]
        assert len(np.unique(station_super_areas)) == 4
        stations._construct_ball_tree()
        station = stations.get_closest_station([0.1, 0])
        assert station.coordinates[0] == 1
        assert station.coordinates[1] == 0
        station = stations.get_closest_station([-50,-10])
        assert station.coordinates[0] == -1
        assert station.coordinates[1] == 0


