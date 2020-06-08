import pandas as pd
import pytest
from june.groups import Household, Households
from june.demography import Person

def test__households_adding():
    household = Household()
    household2 = Household()
    household3 = Household()
    households1 = Households([household])
    households2 = Households([household2, household3])
    households3 = households1 + households2
    assert households3.members == [household, household2, household3]

def test__household_mates():

    house = Household()
    person1 = Person()
    house.add(person1, subgroup_type=house.SubgroupType.kids)
    assert not(person1.housemates)
    person2 = Person()
    house.add(person2, subgroup_type=house.SubgroupType.adults)
    assert person1.housemates[0] == person2
    assert len(person1.housemates) == 1
    assert person2.housemates[0] == person1
    assert len(person2.housemates) == 1
    person3 = Person()
    house.add(person3)
    assert person1.housemates[1] == person3
    assert person2.housemates[1] == person3
    assert person3.housemates[0] == person1
    assert person3.housemates[1] == person2
    for per in [person1, person2, person3]:
        assert len(per.housemates) == 2


