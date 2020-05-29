import yaml
import pytest
from june import paths
from june.distributors.carehome_distributor import CareHomeDistributor, CareHomeError
from june.demography import Person
from june.groups.carehome import CareHome

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
