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
        self.carehome = None
        self.people = []
        for age in range(50, 101):
            for _ in range(0,2):
                man = Person(sex='m', age=age)
                self.people.append(man)
                woman = Person(sex='f', age=age)
                self.people.append(woman)


def test__assertion_no_carehome_residents(carehome_distributor):
    area = MockArea()
    carehome = CareHome(area, n_residents=0)
    area.carehome = carehome
    with pytest.raises(CareHomeError) as e:
        assert carehome_distributor.populate_carehome_in_area(area)
    assert str(e.value) == "No carehome residents in this area."

def test__carehome_populated_correctly(carehome_distributor):
    area = MockArea()
    area.carehome = CareHome(area, n_residents = 10)
    carehome_distributor.populate_carehome_in_area(area)
    assert area.carehome.n_residents == 10
    assert len(area.carehome.people) == 10

