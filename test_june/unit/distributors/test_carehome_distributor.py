import yaml
import pytest
from june import paths
from june.distributors.carehome_distributor import CareHomeDistributor, CareHomeError
from june.demography import Person
from june.groups.carehome import CareHome, CareHomes
from june.geography import Geography
from june.demography import Demography
from june.demography.person import Person
from june.world import World, generate_world_from_geography

default_config_file = paths.configs_path / "defaults/groups/carehome.yaml"

@pytest.fixture(name="carehome_distributor")
def create_carehome_dist():
    carehome_dist = CareHomeDistributor()
    return carehome_dist


@pytest.fixture(name="module_config", scope="module")
def read_config():
    with open(default_config_file) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


class MockSuperArea:
    def __init__(self, module_config):
        self.workers = []
        n_workers = 5
        # workers/carers
        for _ in range(n_workers):
            carer = Person.from_attributes(
            )
            carer.sector = list(module_config["sector"].keys())[0]
            carer.sub_sector = None
            self.workers.append(carer)

class MockArea:
    def __init__(self, module_config):
        self.care_home = None
        self.people = []
        # residents
        for age in range(50, 101):
            for _ in range(0,2):
                man = Person.from_attributes(sex='m', age=age)
                self.people.append(man)
                woman = Person.from_attributes(sex='f', age=age)
                self.people.append(woman)
        # workers/carers
        self.super_area = MockSuperArea(module_config)


def test__assertion_no_carehome_residents(module_config, carehome_distributor):
    area = MockArea(module_config)
    care_home = CareHome(area, n_residents=0, n_workers=0)
    area.care_home = care_home
    with pytest.raises(CareHomeError) as e:
        assert carehome_distributor.populate_care_home_in_area(area)
    assert str(e.value) == "No care home residents in this area."

def test__carehome_populated_correctly(module_config, carehome_distributor):
    area = MockArea(module_config)
    area.care_home = CareHome(area, n_residents = 10, n_workers=2)
    carehome_distributor.populate_care_home_in_area(area)
    assert area.care_home.n_residents == 10
    assert area.care_home.n_workers == 2
    assert len(area.care_home.residents) == 10
    assert len(area.care_home.workers) == 2
    assert len(area.care_home.visitors) == 0

@pytest.fixture(name="world")
def create_area():
    g = Geography.from_file(
        filter_key={"super_area" : ["E02003353"]},
    )
    world = generate_world_from_geography(g)
    return world

def test__carehome_for_geography(world, carehome_distributor):
    # add two workers atificially
    world.care_homes = CareHomes.for_areas(world.areas)
    p1 = Person.from_attributes()
    p1.sector = "Q"
    p2 = Person.from_attributes()
    p2.sector = "Q"
    world.super_areas[0].workers = [p1, p2]
    carehome_distributor.populate_care_home_in_areas(world.areas)
    care_home = world.care_homes[0]
    assert len(care_home.residents) == 24
    assert len(care_home.workers) == 2



