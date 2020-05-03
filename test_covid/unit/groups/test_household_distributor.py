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


class TestAuxiliaryFunctions:
    def test__get_closest_person_of_age(self, household_distributor):
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

    def test__get_matching_partner_is_correct(self, household_distributor):
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

    def test__get_matching_parent(self, household_distributor):
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

    def test__get_matching_second_kid(self, household_distributor):
        area = create_area()
        parent = Person(age=20)
        kid = household_distributor._get_matching_second_kid(parent, area)
        assert kid.age == 0
        parent = Person(age=35)
        kid = household_distributor._get_matching_second_kid(parent, area)
        assert kid.age == 5 or kid.age == 4
        parent = Person(age=80)
        kid = household_distributor._get_matching_second_kid(parent, area)
        assert kid.age == 17


class TestIndividualHouseholdCompositions:
    def test__fill_all_student_households(self, household_distributor):
        area = create_area(age_min=15, age_max=30, people_per_age=5)  # enough students
        # I put these limits to narrow the age range and make it faster, but
        # they do not reflect the expected age of students
        household_distributor.fill_all_student_households(area, 20, 5)
        assert len(area.households) == 5
        for household in area.households:
            for person in household.people:
                assert (
                    household_distributor.STUDENT_MIN_AGE
                    <= person.age
                    <= household_distributor.STUDENT_MAX_AGE
                )

    def test__fill_oldpeople_households(self, household_distributor):
        area = create_area(age_min=50, age_max=100, people_per_age=5)
        # I put these limits to narrow the age range and make it faster, but
        # they do not reflect the expected age of old people
        households_with_extrapeople_list = []
        household_distributor.fill_oldpeople_households(
            2, 10, area, extra_people_lists=(households_with_extrapeople_list,)
        )
        assert len(households_with_extrapeople_list) == 10
        assert len(area.households) == 10
        for household in area.households:
            assert len(household.people) == 2
            for person in household.people:
                assert person.age >= household_distributor.OLD_MIN_AGE

    def test__fill_families_households(self, household_distributor):
        area = create_area(people_per_age=20, age_max=65)
        households_with_extrapeople_list = []
        household_distributor.fill_families_households(
            10, 2, 2, area, extra_people_lists=(households_with_extrapeople_list,)
        )
        assert len(households_with_extrapeople_list) == 10
        assert len(area.households) == 10
        assert len(area.world.households.members) == 10
        for household in area.households:
            assert len(household.people) == 4
            no_of_kids = 0
            no_of_adults = 0
            mother = None
            father = None
            kid_1 = None
            kid_2 = None
            for person in household.people:
                if person.age >= 18:
                    no_of_adults += 1
                    if person.sex == 1:
                        mother = person
                    else:
                        father = person
                else:
                    if kid_1 is None:
                        kid_1 = person
                    else:
                        kid_2 = person
                    no_of_kids += 1
            assert no_of_adults == 2
            assert no_of_kids == 2
            assert father is not None
            assert mother is not None
            if kid_1.age < kid_2.age:
                kid_1, kid_2 = kid_2, kid_1
            assert (mother.age - kid_1.age <= 20) or (mother.age - kid_1.age <= 21)
            assert (mother.age - kid_2.age <= 30) or (mother.age - kid_2.age <= 31)
            assert (father.age - mother.age) in [-1, 0, 1] or (
                father.age - mother.age
            ) in [-1, 0, 1,]

    def test__fill_nokids_households(self, household_distributor):
        area = create_area(age_min=18, people_per_age=10, age_max=70)
        households_with_extrapeople_list = []
        household_distributor.fill_nokids_households(
            adults_per_household=2,
            n_households=10,
            area=area,
            extra_people_lists=(households_with_extrapeople_list,),
        )
        assert len(households_with_extrapeople_list) == 10
        assert len(area.households) == 10
        assert len(area.world.households.members) == 10
        for household in area.households:
            man = None
            woman = None
            for person in household.people:
                assert (
                    household_distributor.ADULT_MIN_AGE
                    <= person.age
                    <= household_distributor.ADULT_MAX_AGE
                )
                if person.sex == 0:
                    man = person
                else:
                    woman = person
            assert man is not None
            assert woman is not None

    def test__fill_youngadult_households(self, household_distributor):
        area = create_area(age_min=15, age_max=40, people_per_age=5)
        households_with_extrapeople_list = []
        household_distributor.fill_youngadult_households(
            3, 20, area, extra_people_lists=(households_with_extrapeople_list,)
        )
        assert len(households_with_extrapeople_list) == 20
        assert len(area.households) == 20
        assert len(area.world.households.members) == 20
        for household in area.households:
            for person in household.people:
                assert (
                    household_distributor.ADULT_MIN_AGE
                    <= person.age
                    <= household_distributor.YOUNG_ADULT_MAX_AGE
                )

    def test__fill_youngadult_with_parents_households(self, household_distributor):
        area = create_area(age_min=15, age_max=40, people_per_age=5)
        households_with_extrapeople_list = []
        household_distributor.fill_youngadult_households(
            3, 20, area, extra_people_lists=(households_with_extrapeople_list,)
        )
        assert len(households_with_extrapeople_list) == 20
        assert len(area.households) == 20
        assert len(area.world.households.members) == 20
        for household in area.households:
            for person in household.people:
                assert (
                    household_distributor.ADULT_MIN_AGE
                    <= person.age
                    <= household_distributor.YOUNG_ADULT_MAX_AGE
                )

    def test__fill_communal_establishments(self, household_distributor):
        area = create_area(people_per_age=5)
        household_distributor.fill_all_communal_establishments(
            n_establishments=5, n_people_in_communal=20, area=area
        )
        assert len(area.households) == 5
        assert len(area.world.households.members) == 5
        for household in area.households:
            assert len(household.people) == 4


class TestMultipleHouseholdCompositions:
    def test__area_is_filled_properly_1(self, household_distributor):
        area = create_area(people_per_age=0)
        men_by_age_counts = {
            5: 4,  # kids
            50: 4,  # adults
            75: 3,  # old people
        }
        area.men_by_age = OrderedDict({})
        area.women_by_age = OrderedDict({})
        for age in men_by_age_counts.keys():
            area.men_by_age[age] = []
            for _ in range(men_by_age_counts[age]):
                person = Person(age=age)
                area.men_by_age[age].append(person)
        composition_numbers = {
            "1 0 >=0 1 0": 4,
            "0 0 0 0 1": 1,
            "0 0 0 0 2": 1,
        }
        household_distributor.distribute_people_to_households(
            area, composition_numbers, 0, 0
        )
        assert len(area.households) == 6
        total_people = 0
        for household in area.households:
            assert len(household.people) <= 6
            kids = 0
            adults = 0
            youngadults = 0
            old = 0
            for person in household.people:
                if 0 <= person.age < household_distributor.ADULT_MIN_AGE:
                    kids += 1
                elif (
                    household_distributor.ADULT_MIN_AGE
                    <= person.age
                    <= household_distributor.YOUNG_ADULT_MAX_AGE
                ):
                    youngadults += 1
                elif (
                    household_distributor.ADULT_MIN_AGE
                    <= person.age
                    < household_distributor.OLD_MIN_AGE
                ):
                    adults += 1
                else:
                    old += 1
            assert kids in [0, 1]
            assert adults in [0, 1]
            assert youngadults in range(0, 7)
            assert old in range(0, 3)
            total_people += old + kids + adults + youngadults

        assert total_people == 11

    def test__area_is_filled_properly_2(self, household_distributor):
        area = create_area(people_per_age=0)
        men_by_age_counts = {
            23: 5,  # young adults or students
            50: 4,  # adults
            75: 3,  # old people
        }
        area.men_by_age = OrderedDict({})
        area.women_by_age = OrderedDict({})
        for age in men_by_age_counts.keys():
            area.men_by_age[age] = []
            for _ in range(men_by_age_counts[age]):
                person = Person(age=age)
                area.men_by_age[age].append(person)
        composition_numbers = {
            "0 0 0 2 0": 2,
            "0 >=1 0 0 0": 1,
            "0 0 0 0 2": 1,
            "0 0 0 0 1": 1,
        }
        household_distributor.distribute_people_to_households(
            area, composition_numbers, 5, 0,
        )
        assert len(area.households) == 5
        total_people = 0
        for household in area.households:
            assert len(household.people) in [1, 2, 5]
            adults = 0
            youngadults = 0
            old = 0
            for person in household.people:
                if (
                    household_distributor.ADULT_MIN_AGE
                    <= person.age
                    <= household_distributor.YOUNG_ADULT_MAX_AGE
                ):
                    youngadults += 1
                elif (
                    household_distributor.ADULT_MIN_AGE
                    <= person.age
                    < household_distributor.OLD_MIN_AGE
                ):
                    adults += 1
                else:
                    old += 1
            assert adults in [0, 2]
            assert youngadults in [0, 5]
            assert old in range(0, 3)
            total_people += old + adults + youngadults

        assert total_people == 12

    def test__area_is_filled_properly_3(self, household_distributor):
        area = create_area(people_per_age=0)
        men_by_age_counts = {
            5: 3,  # kids
            50: 14,  # adults
        }
        area.men_by_age = OrderedDict({})
        area.women_by_age = OrderedDict({})
        for age in men_by_age_counts.keys():
            area.men_by_age[age] = []
            for _ in range(men_by_age_counts[age]):
                person = Person(age=age)
                area.men_by_age[age].append(person)
        composition_numbers = {
            "1 0 >=0 2 0": 1,
            ">=2 0 >=0 2 0": 1,
            ">=0 >=0 >=0 >=0 >=0": 2,
        }
        household_distributor.distribute_people_to_households(
            area, composition_numbers, 0, 10
        )
        assert len(area.households) == 4
        total_people = 0
        for household in area.households:
            assert len(household.people) in [3, 4, 5]
            kids = 0
            adults = 0
            for person in household.people:
                if 0 <= person.age < household_distributor.ADULT_MIN_AGE:
                    kids += 1
                elif (
                    household_distributor.ADULT_MIN_AGE
                    <= person.age
                    < household_distributor.OLD_MIN_AGE
                ):
                    adults += 1
            assert kids in [0, 1, 2]
            assert adults in [2, 5]
            total_people += kids + adults

        assert total_people == 17

class TestCompositionsFromData:

    def test__random_output_area(self, world_ne):
        """
        Let's carefully check the first output area of the test set.
        The area E00062207 has this configuration:
        0 0 0 0 1              15
        0 0 0 1 0              20
        0 0 0 0 2              11
        0 0 0 2 0              24
        1 0 >=0 2 0            12
        >=2 0 >=0 2 0           9
        0 0 >=1 2 0             6
        1 0 >=0 1 0             5
        >=2 0 >=0 1 0           3
        0 0 >=1 1 0             7
        1 0 >=0 >=1 >=0         0
        >=2 0 >=0 >=1 >=0       1
        0 >=1 0 0 0             0
        0 0 0 0 >=2             0
        0 0 >=0 >=0 >=0         1
        >=0 >=0 >=0 >=0 >=0     0
        Name: E00062207, dtype: int64
        """
        area_name = 'E00062207'
        for area in world_ne.areas.members:
            if area.name == area_name:
                break
        household_distributor = HouseholdDistributor.from_inputs(world_ne.inputs)
        composition = world_ne.inputs.household_composition_df.loc[area_name].to_dict()
        total_household_number = sum(list(composition.values()))
        n_students = world_ne.inputs.n_students.loc[area.name].values[0]
        n_people_in_communal = world_ne.inputs.n_in_communal.loc[area.name].values[0]
        household_distributor.distribute_people_to_households(
            area,
            number_households_per_composition=composition,
            n_students=n_students,
            n_people_in_communal=n_people_in_communal,
        )
        # check first that configuration is possible
        olds = 0
        adults = 0
        kids = 0
        youngadults = 0
        for person in area.people:
            if person.age <= 17:
                kids += 1
            elif 18 <= person.age <= 35:
                youngadults += 1
            elif 36 <= person.age <= 64:
                adults += 1
            else:
                olds += 1

        assert kids >= 12 + 9*2 + 5 + 3 * 2 + 2
        assert youngadults >= 6 + 7
        assert adults + youngadults >= 20 + 24 * 2 + 12*2 + 9*2 + 6*2 + 5 + 3 + 7 + 1
        assert olds >= 15 + 11*2
        size_counts = {}
        maxsize = 0
        maxhouse = None
        for household in area.households:
            size = len(household.people)
            if size > maxsize:
                maxsize = size
                maxhouse = household
            if size not in size_counts:
                size_counts[size] = 0
            size_counts[size] += 1
        assert size_counts[1] >= 35
        assert size_counts[2] >= 35
        # check if they have the right amount of kids
        have_kids = 0
        have_olds = 0
        counter = 0
        for household in area.households:
            has_kids = False
            has_olds = False
            for person in household.people:
                if person.age < 18:
                    has_kids = True
                elif person.age >= 65:
                    counter += 1
                    has_olds = True
            have_kids += int(has_kids)
            have_olds += int(has_olds)

        assert have_kids >= 12 + 9 + 5 + 3 + 1
        assert 15 + 11 <= have_olds 
        print("house with maxsize has ages")
        for person in maxhouse.people:
            print(person.age)
        assert maxsize <= 6
        assert len(area.households) >= total_household_number



