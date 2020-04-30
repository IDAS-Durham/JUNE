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
    def __init__(self, age_min=0, age_max=99, people_per_age=5):
        self.create_dicts(age_min, age_max, people_per_age)
        self.n_people = (age_max - age_min + 1) * people_per_age
        self.world = MockWorld()
        self.households = []

    def create_dicts(self, age_min, age_max, people_per_age):
        self.men_by_age = create_men_by_age_dict(age_min, age_max, people_per_age)
        self.women_by_age = create_women_by_age_dict(age_min, age_max, people_per_age)


def create_men_by_age_dict(age_min=0, age_max=99, people_per_age=5):
    ages = np.arange(age_min, age_max)
    men_by_age = OrderedDict({})
    for age in ages:
        men_by_age[age] = []
        for _ in range(0, people_per_age):
            man = Person(sex=0, age=age)
            men_by_age[age].append(man)
    return men_by_age


def create_women_by_age_dict(age_min=0, age_max=99, people_per_age=5):
    ages = np.arange(age_min, age_max)
    women_by_age = OrderedDict({})
    for age in ages:
        women_by_age[age] = []
        for _ in range(0, people_per_age):
            woman = Person(sex=1, age=age)
            women_by_age[age].append(woman)
    return women_by_age


def create_area(age_min=0, age_max=99, people_per_age=5):
    area = MockArea(age_min, age_max, people_per_age)
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
    first_kid_parent_age_differences = [20, 21]
    first_kid_parent_age_differences_probabilities = [0.5, 0.5]
    second_kid_parent_age_differences = [30, 31]
    second_kid_parent_age_differences_probabilities = [0.5, 0.5]
    couples_age_differences = [0, 1]
    couples_age_differences_probabilities = [0.5, 0.5]
    hd = HouseholdDistributor(
        first_kid_parent_age_differences,
        first_kid_parent_age_differences_probabilities,
        second_kid_parent_age_differences,
        second_kid_parent_age_differences_probabilities,
        couples_age_differences,
        couples_age_differences_probabilities,
    )
    return hd


def test__get_closest_person_of_age(household_distributor):
    area = create_area(people_per_age=1)
    print(len(area.men_by_age[50]))
    # check normal use
    age = 35
    man = household_distributor._get_closest_person_of_age(
        area.men_by_age, area.women_by_age, age
    )
    assert man.sex == 0
    assert man.age == 35
    assert 35 not in area.men_by_age.keys()  # check key has been deleted

    age = 0
    kid = household_distributor._get_closest_person_of_age(
        area.women_by_age, area.men_by_age, 0
    )
    assert kid.sex == 1
    assert kid.age == 0

    # assert returns none when can't find someone in the allowed age range
    none_person = household_distributor._get_closest_person_of_age(
        area.men_by_age, area.women_by_age, 45, min_age=20, max_age=25
    )
    assert none_person is None

    for key in range(40, 51):
        del area.men_by_age[key]
    none_person = household_distributor._get_closest_person_of_age(
        area.men_by_age, {}, 45, min_age=40, max_age=50
    )
    assert none_person is None

    # assert return opposite sex if the option is available
    woman = household_distributor._get_closest_person_of_age(
        area.men_by_age, area.women_by_age, 45, min_age=40, max_age=50
    )
    assert woman.sex == 1
    assert woman.age == 45


def test__get_matching_partner_is_correct(household_distributor):
    area = create_area(people_per_age=5)
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


def test__get_matching_parent(household_distributor):
    area = create_area()
    kid = Person(age=10)
    parent = household_distributor._get_matching_parent(kid, area)
    assert parent.age == 30 or parent.age == 31
    assert parent.sex == 1

    # check if no adult women available it returns men
    age_min_parent = kid.age + 18
    age_max_parent = household_distributor.MAX_AGE_TO_BE_PARENT
    for key in range(age_min_parent, age_max_parent + 1):
        del area.women_by_age[key]
    male_parent = household_distributor._get_matching_parent(kid, area)
    assert male_parent.sex == 0
    assert male_parent.age == 30 or male_parent.age == 31

    # check if no adults available it returns None
    for key in range(age_min_parent, age_max_parent + 1):
        del area.men_by_age[key]
    none_parent = household_distributor._get_matching_parent(kid, area)
    assert none_parent == None


def test__get_matching_second_kid(household_distributor):
    area = create_area()
    parent = Person(age=20)
    kid = household_distributor._get_matching_second_kid(parent, area)
    assert kid.age == 0
    parent = Person(age=35)
    kid = household_distributor._get_matching_second_kid(parent, area)
    assert kid.age == 5 or kid.age == 4
    parent = Person(age=80)
    kid = household_distributor._get_matching_second_kid(parent, area)
    assert kid is None


def test__fill_all_student_households(household_distributor):
    area = create_area(people_per_age=5)  # enough students
    household_distributor.fill_all_student_households(area, 20, 5)
    assert len(area.households) == 5
