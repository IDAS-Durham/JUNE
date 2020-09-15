from pathlib import Path

from june.geography import City, Cities, Area, Areas

city_test_file = Path(__file__).parent / "cities.csv"


class TestCity:
    def test__city_setup(self):
        city = City(name="Durham", areas=["A1", "A2"])
        assert city.name == "Durham"
        assert city.areas == ["A1", "A2"]

    def test__city_setup_from_file(self):
        city = City.from_file(name="Durham", city_areas_filename=city_test_file)
        assert list(city.areas) == ["a1", "a2"]
        city = City.from_file(name="Newcastle", city_areas_filename=city_test_file)
        assert list(city.areas) == ["b1"]
        city = City.from_file(name="Leeds", city_areas_filename=city_test_file)
        assert list(city.areas) == ["c1", "c2", "c3"]

    def test__cities_for_areas(self):
        areas = Areas([Area(name="c1"), Area(name="c2")], ball_tree=False)
        cities = Cities.for_areas(areas, city_areas_filename=city_test_file)
        assert cities[0].name == "Leeds"
        assert list(cities[0].areas) == ["c1", "c2"]


