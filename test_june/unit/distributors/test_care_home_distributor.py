import yaml
import pytest
from june import paths
from june.distributors.care_home_distributor import CareHomeDistributor, CareHomeError
from june.demography import Person
from june.groups.care_home import CareHome, CareHomes
from june.geography import Geography, Area, SuperArea, Areas, SuperAreas
from june.demography import Demography
from june.demography.person import Person
from june.world import World, generate_world_from_geography

default_config_file = paths.configs_path / "defaults/groups/carehome.yaml"


@pytest.fixture(name="geography", scope="module")
def make_geo():
    super_areas = SuperAreas(
        [SuperArea(name="super_area_1"), SuperArea(name="super_area_2")],
        ball_tree=False,
    )
    areas = Areas(
        [
            Area(super_area=super_areas[0], name="area_1"),
            Area(super_area=super_areas[0], name="area_2"),
            Area(super_area=super_areas[1], name="area_3"),
            Area(super_area=super_areas[1], name="area_4"),
        ],
        ball_tree=False,
    )
    super_areas[0].areas = areas[0:2]
    super_areas[1].areas = areas[2:4]
    # workers/carers
    for _ in range(5):
        carer = Person.from_attributes()
        carer.sector = "Q"
        carer.sub_sector = None
        super_areas[0].workers.append(carer)
    for _ in range(3):
        carer = Person.from_attributes()
        carer.sector = "Q"
        carer.sub_sector = None
        super_areas[1].workers.append(carer)

    # residents
    # super area 1
    for _ in range(10):
        person = Person.from_attributes(age=40, sex="m")
        areas[0].people.append(person)
    for _ in range(10):
        person = Person.from_attributes(age=80, sex="f")
        areas[0].people.append(person)

    for _ in range(30):
        person = Person.from_attributes(age=80, sex="m")
        areas[1].people.append(person)
    for _ in range(20):
        person = Person.from_attributes(age=40, sex="f")
        areas[1].people.append(person)

    # super area 2
    for _ in range(5):
        person = Person.from_attributes(age=40, sex="m")
        areas[2].people.append(person)
    for _ in range(12):
        person = Person.from_attributes(age=80, sex="f")
        areas[2].people.append(person)

    for _ in range(10):
        person = Person.from_attributes(age=80, sex="m")
        areas[3].people.append(person)
    for _ in range(8):
        person = Person.from_attributes(age=40, sex="f")
        areas[3].people.append(person)

    # workers
    super_areas[0].workers = []
    for _ in range(30):
        person = Person.from_attributes(age=28)
        person.sector = "Q"
        person.sub_sector = None
        super_areas[0].workers.append(person)
    super_areas[1].workers = []
    for _ in range(70):
        person = Person.from_attributes(age=28)
        person.sector = "Q"
        person.sub_sector = None
        super_areas[1].workers.append(person)

    areas[0].care_home = CareHome(n_residents=20, n_workers= 10, area=areas[0])
    areas[1].care_home = CareHome(n_residents=50, n_workers= 20, area=areas[1])
    areas[2].care_home = CareHome(n_residents=17, n_workers= 30, area=areas[2])
    areas[3].care_home = CareHome(n_residents=18, n_workers= 40, area=areas[3])

    return areas, super_areas


class TestCareHomeDistributor:
    @pytest.fixture(name="carehome_distributor")
    def create_carehome_dist(self):
        communal_men_by_super_area = {
            "super_area_1": {"0-60": 10, "60-100": 30},
            "super_area_2": {"0-50": 5, "50-100": 10},
        }
        communal_women_by_super_area = {
            "super_area_1": {"0-60": 20, "60-100": 10},
            "super_area_2": {"0-50": 8, "50-100": 12},
        }
        carehome_dist = CareHomeDistributor(
            communal_men_by_super_area=communal_men_by_super_area,
            communal_women_by_super_area=communal_women_by_super_area,
        )
        return carehome_dist

    def _count_people_in_carehome(self, area):
        men = []
        women = []
        for person in area.care_home.residents:
            if person.sex == "m":
                men.append(person)
            else:
                women.append(person)
        return men, women

    def test__care_home_residents(self, carehome_distributor, geography):
        areas, super_areas = geography
        carehome_distributor.populate_care_homes_in_super_areas(super_areas=super_areas)

        men, women = self._count_people_in_carehome(areas[0])
        assert len(men) == 10
        assert len(women) == 10
        for man in men:
            assert man.age == 40
        for woman in women:
            assert woman.age == 80

        men, women = self._count_people_in_carehome(areas[1])
        assert len(men) == 30
        assert len(women) == 20
        for man in men:
            assert man.age == 80
        for woman in women:
            assert woman.age == 40

        men, women = self._count_people_in_carehome(areas[2])
        assert len(men) == 5
        assert len(women) == 12
        for man in men:
            assert man.age == 40
        for woman in women:
            assert woman.age == 80

        men, women = self._count_people_in_carehome(areas[3])
        assert len(men) == 10
        assert len(women) == 8
        for man in men:
            assert man.age == 80
        for woman in women:
            assert woman.age == 40

    def test__carehome_workers(self, carehome_distributor, geography):
        areas, super_areas = geography
        carehome_distributor.distribute_workers_to_care_homes(super_areas=super_areas)
        for area in areas:
            assert len(area.care_home.workers) == area.care_home.n_workers
            for worker in area.care_home.workers:
                assert worker.sector == "Q"


