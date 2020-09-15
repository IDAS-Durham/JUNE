from pathlib import Path

from june.geography import City, Cities, SuperArea, SuperAreas

city_test_file = Path(__file__).parent / "cities.csv"


class TestCity:
    def test__city_setup(self):
        city = City(name="Durham", super_areas=["A1", "A2"])
        assert city.name == "Durham"
        assert city.super_areas == ["A1", "A2"]

    def test__city_setup_from_file(self):
        city = City.from_file(name="Durham", city_super_areas_filename=city_test_file)
        assert list(city.super_areas) == ["a1", "a2"]
        city = City.from_file(
            name="Newcastle", city_super_areas_filename=city_test_file
        )
        assert list(city.super_areas) == ["b1"]
        city = City.from_file(name="Leeds", city_super_areas_filename=city_test_file)
        assert list(city.super_areas) == ["c1", "c2", "c3"]

    def test__cities_for_super_areas(self):
        super_areas = SuperAreas(
            [
                SuperArea(name="c1", coordinates=[1, 2]),
                SuperArea(name="c2", coordinates=[3, 4]),
            ],
        )
        cities = Cities.for_super_areas(
            super_areas, city_super_areas_filename=city_test_file
        )
        assert cities[0].name == "Leeds"
        assert super_areas[0].city == cities[0]
        assert super_areas[1].city == cities[0]
        assert list(cities[0].super_areas) == ["c1", "c2"]
