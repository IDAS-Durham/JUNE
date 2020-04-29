import numpy as np
import os
from covid.groups import Household, HouseholdDistributor, Households, Person
import pytest


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


def create_people_by_age_dict(sex, number_per_age=100):
    ages = np.arange(0, 100)
    women_by_age = OrderedDict({})
    for age in ages:
        women_by_age[age] = []
        for _ in range(number_per_age):
            person = Person(sex=sex, age=age)
            women_by_age[age].append(person)
    return women_by_age


def test__get_matching_partner_is_correct():

    women_by_age = create_people_by_age_dict(1, 100)
    hdistributor = HouseholdDistributor(women_by_age=women_by_age)
    person = Person(sex=0, age=40)
    matching_women_ages = []
    for _ in range(200):
        matching_woman = hdistributor.get_matching_partner(age=40, sex=0)
        assert matching_woman.sex == 1
        matching_women_ages.append(matching_woman.age)

    # here check is gaussian
    # repeat for man


def test__get_matching_parent_is_correct():
    kid = Person(age=20)
    hdistributor = HouseholdDistributor(
        men_by_age=men_by_age, women_by_age=women_by_age
    )
    matching_kids = []
    for _ in range(50):
        matching_kid_to_parent = hdistributor.get_matching_kid_to_parent(parent)
        matching_kids.append(matching_kid_to_parent)

    # assert is gaussian
