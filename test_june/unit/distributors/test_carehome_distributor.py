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
    with open(config_file) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


class MockSuperArea:
    def __init__(self, module_config):
        self.workers = []
        n_workers = 2
        # workers/carers
        for _ in range(n_workers):
            carer = Person(
                sector = list(module_config["sector"].keys())[0]
                sub_sector = None,
            )
            self.workers.append(carer)

class MockArea:
    def __init__(self):
        self.care_home = None
        self.people = []
        # residents
        for age in range(50, 101):
            for _ in range(0,2):
                man = Person(sex='m', age=age)
                self.people.append(man)
                woman = Person(sex='f', age=age)
                self.people.append(woman)
        # workers/carers
        self.super_area = MockSuperArea()


def test__assertion_no_carehome_residents(carehome_distributor):
    area = MockArea()
    care_home = CareHome(area, n_residents=0)
    area.care_home = care_home
    with pytest.raises(CareHomeError) as e:
        assert carehome_distributor.populate_care_home_in_area(area)
    assert str(e.value) == "No care home residents in this area."

def test__carehome_populated_correctly(carehome_distributor):
    area = MockArea()
    area.care_home = CareHome(area, n_residents = 10)
    carehome_distributor.populate_care_home_in_area(area)
    assert area.care_home.n_residents == 10
    assert len(area.care_home.people) == 10
