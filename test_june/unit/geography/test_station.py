from pathlib import Path
import numpy as np

from june.geography import Area, Areas, Station, Stations, City, Cities, SuperArea
from june.geography import Station, Stations, StationHub, StationHubs

stations_test_file = Path(__file__).parent / "stations.csv"

class TestStations:
    def test__stations_setup(self):
        station = Station(name="King's Cross", area="l1")
        assert station.area == "l1"
        assert station.name == "King's Cross"

    def test__stations_from_file(self):
        stations = Stations.from_file(
            areas=["l1", "l2"], station_areas_filename=stations_test_file
        )
        assert stations[0].area == "l1"
        assert stations[0].name == "King's Cross"
        assert stations[1].area == "l2"
        assert stations[1].name == "Victoria"

    def test__stations_for_city(self):
        city = City(name="London", areas=["l1", "l2"])
        stations = Stations.for_city(
            city=city, station_areas_filename=stations_test_file
        )
        assert stations[0].area == "l1"
        assert stations[0].name == "King's Cross"
        assert stations[1].area == "l2"
        assert stations[1].name == "Victoria"
        assert stations[0].city == city
        assert stations[1].city == city

    def test__station_coordinates(self):
        areas = Areas(
            [Area(name="c1", coordinates=[1, 2]), Area(name="c2", coordinates=[3, 4])],
            ball_tree=False,
        )
        station = Station(area="c1")
        assert station.get_coordinates(areas) == [1, 2]
        station = Station(area="c2")
        assert station.get_coordinates(areas) == [3, 4]


class TestHubs:
    def test__hubs_setup(self):
        hub = StationHub(station="Sants", city="Barcelona", area=Area(name="b1"))
        assert hub.station == "Sants"
        assert hub.city == "Barcelona"
        assert hub.area.name == "b1"

    def test__hubs_for_station(self):
        areas = Areas(
            [
                Area(name="b1", coordinates=[0, 0]),
                Area(name="b2", coordinates=[1, 0]),
                Area(name="b3", coordinates=[0, 1]),
                Area(name="b4", coordinates=[-1, 0]),
                Area(name="b5", coordinates=[0, -1]),
            ],
            ball_tree=True,
        )
        station = Station(name="Sants", area="b1")
        station_coordinates = station.get_coordinates(areas)
        assert station_coordinates == [0, 0]
        hubs = StationHubs.for_station(
            station=station, number_of_hubs=4, distance_to_station=500, areas = areas
        )
        assert len(hubs) == 4
        hub_areas = []
        for hub in hubs:
            hub_areas.append(hub.area.name)
            assert hub.station == station.name
            assert hub.city == station.city
            assert hub.area.name in ["b1", "b2", "b3", "b4", "b5"]
        assert len(np.unique(hub_areas)) == 4
        hub = hubs.get_closest_hub([0.1, 0])
        assert hub.coordinates[0] == 1
        assert hub.coordinates[1] == 0
        hub = hubs.get_closest_hub([-50,-10])
        assert hub.coordinates[0] == -1
        assert hub.coordinates[1] == 0


