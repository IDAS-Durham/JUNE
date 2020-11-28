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
    person1 = Person.from_attributes()
    house.add(person1, subgroup_type=house.SubgroupType.kids)
    assert house.residents[0] == person1
    person2 = Person.from_attributes()
    person3 = Person.from_attributes()
    house.add(person2)
    house.add(person3)
    assert person1 in person1.housemates
    assert person2 in person1.housemates
    assert person3 in person1.housemates

def test__being_visited_flag():
    house = Household()
    person = Person.from_attributes()
    assert not house.being_visited
    house.add(person, activity="leisure")
    assert house.being_visited
    house.being_visited = False
    house.add(person)
    assert not house.being_visited
