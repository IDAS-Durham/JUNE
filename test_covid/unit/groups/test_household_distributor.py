import numpy as np
import os
from covid.groups import Household, HouseholdDistributor, Households, Person
import pytest

@pytest.fixture(name="number_households_per_composition")
def create_household_composition_example():
    ret = {
            "0 0 0 1 0" : 2,
            "0 0 0 0 1" : 1,
            "0 0 0 0 2" : 1,
            "2 0 0 2 0" : 1,
            }
    return ret


def test__get_matching_woman_is_gaussian():
    ages = np.arange(0,100)
    women_by_age = OrderedDict({})
    for age in ages:
        women_by_age[age] = []
        for _ in range(100):
            person = Person(sex=1, age=age)
            women_by_age[age].append(person) 

    hdistributor = HouseholdDistributor(women_by_age=women_by_age)
    person = Person(sex=0, age=40)
    matching_women_ages = []
    for _ in range(200):
        matching_woman = hdistributor.get_matching_person(age=40, sex=0)
        assert (matching_woman.sex == 1)
        matching_women_ages.append(matching_woman.age)

    # here check is gaussian
    # repeat for man

def 









