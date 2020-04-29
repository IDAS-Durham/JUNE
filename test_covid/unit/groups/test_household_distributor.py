import numpy as np
import os
from covid.groups import Household, HouseholdDistributor, Households, Person
import pytest
from collections import OrderedDict
from covid.groups import Person
from pathlib import Path

class MockHouseholds:
    def __init__(self):
        self.members = []

class MockWorld:
    def __init__(self):
        self.households = MockHouseholds()

class MockArea:
    def __init__(self):
        self.create_dicts()

    def create_dicts(self):
        self.men_by_age = create_men_by_age_dict()
        self.women_by_age = create_women_by_age_dict()

def create_men_by_age_dict():
    ages = np.arange(0,99)
    men_by_age = OrderedDict({})
    for age in ages:
        men_by_age[age] = []
        for _ in range(0,50):
            man = Person(sex=0, age=age)
            men_by_age[age].append(man)
    return men_by_age

def create_women_by_age_dict():
    ages = np.arange(0,99)
    women_by_age = OrderedDict({})
    for age in ages:
        women_by_age[age] = []
        for _ in range(0,50):
            woman = Person(sex=1, age=age)
            women_by_age[age].append(woman)
    return women_by_age

def create_area():
    area = MockArea()
    return area

@pytest.fixture(name="number_households_per_composition")
def create_household_composition_example():
    ret = {
        "1 0 >1 1 0": 2,
        "0 0 0 0 1": 1,
        "0 0 0 0 2": 1,
        ">2 0 0 2 0": 1,
    }
    return ret


@pytest.fixture(name="household_distributor")
def create_household_distributor():
    kid_parent_age_differences = [20, 21]
    kid_parent_age_differences_probabilities = [0.5, 0.5]
    couples_age_differences = [0, 1]
    couples_age_differences_probabilities = [0.5, 0.5]
    hd = HouseholdDistributor(
        kid_parent_age_differences,
        kid_parent_age_differences_probabilities,
        kid_parent_age_differences,
        kid_parent_age_differences_probabilities,
        couples_age_differences,
        couples_age_differences_probabilities,
    )
    return hd

def test__get_matching_partner_is_correct(household_distributor):
    area = create_area()
    man = Person(sex=0, age=40)
    woman = household_distributor._get_matching_partner(man, area)
    assert woman.sex == 1
    assert (woman.age == 40) or (woman.age == 41)
    woman = Person(sex=1, age=40)
    man = household_distributor._get_matching_partner(woman, area)
    assert man.sex == 0
    assert (man.age == 40) or (man.age == 41)
    # check we get same sex if not available
    area.men_by_age = {}
    woman = household_distributor._get_matching_partner(woman, area)
    assert woman.sex == 1
    assert (woman.age == 40) or (woman.age == 41)


