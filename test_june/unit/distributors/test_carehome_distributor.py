import pytest
from june.distributors.carehome_distributor import CareHomeDistributor, CareHomeError
from june.demography import Person
from june.groups.carehome import CareHome

@pytest.fixture(name="carehome_distributor")
def create_carehome_dist():
    carehome_dist = CareHomeDistributor()
    return carehome_dist

class MockArea:
    def __init__(self):
        self.care_home = None
        self.people = []
        for age in range(50, 101):
            for _ in range(0,2):
                man = Person(sex='m', age=age)
                self.people.append(man)
                woman = Person(sex='f', age=age)
                self.people.append(woman)


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

