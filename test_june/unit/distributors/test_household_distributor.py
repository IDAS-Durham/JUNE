import os
from pathlib import Path
from collections import OrderedDict

import numpy as np
import pytest

from june.demography.person import Person
from june.demography import Demography
from june.geography import Geography
from june.groups import Household, Households
from june.distributors import HouseholdDistributor


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


@pytest.fixture(name="household_distributor", scope="module")
def create_household_distributor():
    first_kid_parent_age_differences = {20: 0.5, 21: 0.5}
    second_kid_parent_age_differences = {30: 0.5, 31: 0.5}
    couples_age_differences = {0: 0.5, 1: 0.5}
    hd = HouseholdDistributor(
        first_kid_parent_age_differences,
        second_kid_parent_age_differences,
        couples_age_differences,
    )
    return hd


class TestAuxiliaryFunctions:
    def test__get_closest_person_of_age(self, household_distributor):
        area = create_area(people_per_age=1)
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

    def test__get_random_person_in_age_bracket(self, household_distributor):
        area = create_area(people_per_age=1)
        # check normal use
        person_1 = household_distributor._get_random_person_in_age_bracket(
            area.men_by_age, area.women_by_age, min_age=18, max_age=18
        )
        person_2 = household_distributor._get_random_person_in_age_bracket(
            area.men_by_age, area.women_by_age, min_age=18, max_age=18
        )
        assert person_1.age == 18
        assert person_2.age == 18
        assert person_1.sex != person_2.sex

    def test__get_matching_partner_is_correct(self, household_distributor):
        area = create_area(people_per_age=5)
        man = Person(sex=0, age=40)
        woman = household_distributor._get_matching_partner(
            man, area.men_by_age, area.women_by_age
        )
        assert woman.sex == 1
        assert (woman.age == 40) or (woman.age == 41)
        woman = Person(sex=1, age=40)
        man = household_distributor._get_matching_partner(
            woman, area.men_by_age, area.women_by_age
        )
        assert man.sex == 0
        assert (man.age == 40) or (man.age == 41)
        # check option to get under or over 65
        person = Person(sex=1, age=76)
        partner = household_distributor._get_matching_partner(
            person, area.men_by_age, area.women_by_age, under_65=True
        )
        assert partner.age < 65
        assert partner.sex == 0
        partner2 = household_distributor._get_matching_partner(
            person, area.men_by_age, area.women_by_age, over_65=True
        )
        assert partner2.age > 65
        assert partner2.sex == 0
        # check we get same sex if not available
        area.men_by_age = {}
        woman = household_distributor._get_matching_partner(
            woman, area.men_by_age, area.women_by_age,
        )
        assert woman.sex == 1
        assert (woman.age == 40) or (woman.age == 41)

    def test__get_matching_parent(self, household_distributor):
        area = create_area()
        kid = Person(age=10)
        parent = household_distributor._get_matching_parent(
            kid, area.men_by_age, area.women_by_age,
        )
        assert parent.age == 30 or parent.age == 31
        assert parent.sex == 1

        # check if no adult women available it returns men
        age_min_parent = 18
        age_max_parent = household_distributor.max_age_to_be_parent
        for key in range(age_min_parent, age_max_parent + 1):
            del area.women_by_age[key]
        male_parent = household_distributor._get_matching_parent(
            kid, area.men_by_age, area.women_by_age,
        )
        assert male_parent.sex == 0
        assert male_parent.age == 30 or male_parent.age == 31

        # check if no adults available it returns None
        for key in range(age_min_parent, age_max_parent + 1):
            del area.men_by_age[key]
        none_parent = household_distributor._get_matching_parent(
            kid, area.men_by_age, area.women_by_age,
        )
        assert none_parent == None

    def test__get_matching_second_kid(self, household_distributor):
        area = create_area()
        parent = Person(age=20)
        kid = household_distributor._get_matching_second_kid(
            parent, area.men_by_age, area.women_by_age,
        )
        assert kid.age == 0
        parent = Person(age=35)
        kid = household_distributor._get_matching_second_kid(
            parent, area.men_by_age, area.women_by_age,
        )
        assert kid.age == 5 or kid.age == 4
        parent = Person(age=80)
        kid = household_distributor._get_matching_second_kid(
            parent, area.men_by_age, area.women_by_age,
        )
        assert kid.age == 17


class TestIndividualHouseholdCompositions:
    def test__fill_all_student_households(self, household_distributor):
        area = create_area(age_min=15, age_max=30, people_per_age=5)  # enough students
        # I put these limits to narrow the age range and make it faster, but
        # they do not reflect the expected age of students
        area.households = household_distributor.fill_all_student_households(
            area.men_by_age,
            area.women_by_age,
            area,
            n_students=20,
            student_houses_number=5,
        )
        assert len(area.households) == 5
        counter = 0
        for household in area.households:
            for person in household.people:
                counter += 1
                assert (
                    household_distributor.student_min_age
                    <= person.age
                    <= household_distributor.student_max_age
                )
        assert counter == 20
        area.households = []
        area.households = household_distributor.fill_all_student_households(
            area.men_by_age,
            area.women_by_age,
            area,
            n_students=11,
            student_houses_number=3,
        )
        assert len(area.households) == 3

    def test__fill_oldpeople_households(self, household_distributor):
        area = create_area(age_min=50, age_max=100, people_per_age=20)
        # I put these limits to narrow the age range and make it faster, but
        # they do not reflect the expected age of old people
        households_with_extrapeople_list = []
        area.households = household_distributor.fill_oldpeople_households(
            area.men_by_age,
            area.women_by_age,
            2,
            10,
            area,
            extra_people_lists=(households_with_extrapeople_list,),
        )
        assert len(households_with_extrapeople_list) == 10
        assert len(area.households) == 10
        for household in area.households:
            assert len(household.people) == 2
            for person in household.people:
                assert person.age >= household_distributor.old_min_age
        households_with_extrapeople_list = []
        area.households += household_distributor.fill_oldpeople_households(
            area.men_by_age,
            area.women_by_age,
            2,
            10,
            area,
            extra_people_lists=(households_with_extrapeople_list,),
            max_household_size=2,
        )
        assert len(area.households) == 20
        assert len(households_with_extrapeople_list) == 0  # no spaces left
        for household in area.households:
            assert len(household.people) == 2
            for person in household.people:
                assert person.age >= household_distributor.old_min_age

    def test__fill_families_households(self, household_distributor):
        area = create_area(people_per_age=20, age_max=65)
        households_with_extrapeople_list = []
        area.households = household_distributor.fill_families_households(
            area.men_by_age,
            area.women_by_age,
            n_households=10,
            kids_per_house=2,
            parents_per_house=2,
            old_per_house=0,
            area=area,
            extra_people_lists=(households_with_extrapeople_list,),
        )
        assert len(households_with_extrapeople_list) == 10
        assert len(area.households) == 10
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
        area = create_area(age_min=18, people_per_age=10, age_max=60)
        households_with_extrapeople_list = []
        area.households = household_distributor.fill_nokids_households(
            area.men_by_age,
            area.women_by_age,
            adults_per_household=2,
            n_households=10,
            area=area,
            extra_people_lists=(households_with_extrapeople_list,),
        )
        assert len(households_with_extrapeople_list) == 10
        assert len(area.households) == 10
        for household in area.households:
            man = None
            woman = None
            oldpeople = 0
            for person in household.people:
                assert (
                    household_distributor.adult_min_age
                    <= person.age
                    <= household_distributor.old_max_age
                )
                if person.age >= household_distributor.old_min_age:
                    oldpeople += 1
                if person.sex == 0:
                    man = person
                else:
                    woman = person
            assert man is not None
            assert woman is not None
            assert oldpeople <= 1

    def test__fill_youngadult_households(self, household_distributor):
        area = create_area(age_min=15, age_max=40, people_per_age=5)
        households_with_extrapeople_list = []
        area.households = household_distributor.fill_youngadult_households(
            area.men_by_age,
            area.women_by_age,
            3,
            20,
            area,
            extra_people_lists=(households_with_extrapeople_list,),
        )
        assert len(households_with_extrapeople_list) == 20
        assert len(area.households) == 20
        for household in area.households:
            for person in household.people:
                assert (
                    household_distributor.adult_min_age
                    <= person.age
                    <= household_distributor.young_adult_max_age
                )

    def test__fill_youngadult_with_parents_households(self, household_distributor):
        area = create_area(age_min=15, age_max=40, people_per_age=5)
        households_with_extrapeople_list = []
        area.households = household_distributor.fill_youngadult_households(
            area.men_by_age,
            area.women_by_age,
            3,
            20,
            area,
            extra_people_lists=(households_with_extrapeople_list,),
        )
        assert len(households_with_extrapeople_list) == 20
        assert len(area.households) == 20
        for household in area.households:
            for person in household.people:
                assert (
                    household_distributor.adult_min_age
                    <= person.age
                    <= household_distributor.young_adult_max_age
                )

    def test__fill_communal_establishments(self, household_distributor):
        area = create_area(people_per_age=5)
        area.households = household_distributor.fill_all_communal_establishments(
            area.men_by_age,
            area.women_by_age,
            n_establishments=5,
            n_people_in_communal=20,
            area=area,
        )
        assert len(area.households) == 5
        for household in area.households:
            assert len(household.people) == 4
        area.households = []
        area.households = household_distributor.fill_all_communal_establishments(
            area.men_by_age,
            area.women_by_age,
            n_establishments=2,
            n_people_in_communal=7,
            area=area,
        )
        assert len(area.households) == 2
        for household in area.households:
            assert len(household.people) in [3, 4]


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
        area.households = household_distributor.distribute_people_to_households(
            area.men_by_age, area.women_by_age, area, composition_numbers, 0, 0
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
                if 0 <= person.age < household_distributor.adult_min_age:
                    kids += 1
                elif (
                    household_distributor.adult_min_age
                    <= person.age
                    <= household_distributor.young_adult_max_age
                ):
                    youngadults += 1
                elif (
                    household_distributor.adult_min_age
                    <= person.age
                    < household_distributor.old_min_age
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
        area.households = household_distributor.distribute_people_to_households(
            area.men_by_age, area.women_by_age, area, composition_numbers, 5, 0,
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
                    household_distributor.adult_min_age
                    <= person.age
                    <= household_distributor.young_adult_max_age
                ):
                    youngadults += 1
                elif (
                    household_distributor.adult_min_age
                    <= person.age
                    < household_distributor.old_min_age
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
        area.households = household_distributor.distribute_people_to_households(
            area.men_by_age, area.women_by_age, area, composition_numbers, 0, 10
        )
        assert len(area.households) == 4
        total_people = 0
        for household in area.households:
            assert len(household.people) in [3, 4, 5]
            kids = 0
            adults = 0
            for person in household.people:
                if 0 <= person.age < household_distributor.adult_min_age:
                    kids += 1
                elif (
                    household_distributor.adult_min_age
                    <= person.age
                    <= household_distributor.adult_max_age
                ):
                    adults += 1
            assert kids in [0, 1, 2]
            assert adults in [2, 5]
            total_people += kids + adults

        assert total_people == 17



#class TestSpecificArea:
#    """
#    Let's carefully check the first output area of the test set.
#    This area has no carehomes so we don't have to account for them.
#    The area E00062207 has this configuration:
#    0 0 0 0 1              15
#    0 0 0 1 0              20
#    0 0 0 0 2              11
#    0 0 0 2 0              24
#    1 0 >=0 2 0            12
#    >=2 0 >=0 2 0           9
#    0 0 >=1 2 0             6
#    1 0 >=0 1 0             5
#    >=2 0 >=0 1 0           3
#    0 0 >=1 1 0             7
#    1 0 >=0 >=1 >=0         0
#    >=2 0 >=0 >=1 >=0       1
#    0 >=1 0 0 0             0
#    0 0 0 0 >=2             0
#    0 0 >=0 >=0 >=0         1
#    >=0 >=0 >=0 >=0 >=0     0
#    Name: E00062207, dtype: int64
#    """
#    @pytest.fixture(name="example_area", scope="module")
#    def make_geo(self):
#        geo = Geography.from_file({"oa": ["E00062207"]})
#        dem = Demography.for_geography(geo)
#        geo.areas[0].populate(dem)
#        return geo.areas[0]
#
#    @pytest.fixture(name="hd_area", scope="module")
#    def populate_example_area(self, example_area):
#        area = example_area
#        household_distributor = HouseholdDistributor.from_file()
#        household_distributor.distribute_people_and_households_to_areas(
#            [area],
#        )
#        return household_distributor
#
#    def test__all_household_have_reasonable_size(
#        self, example_area, hd_area
#    ):
#        sizes_dict = {}
#        for household in example_area.households:
#            size = len(household.people)
#            if size not in sizes_dict:
#                sizes_dict[size] = 0
#            sizes_dict[size] += 1
#
#        assert max(list(sizes_dict.keys())) <= 8
#        assert sizes_dict[2] >= 35
#        assert sizes_dict[1] >= 35
#
#    def test__oldpeople_have_suitable_accomodation(
#        self, example_area,
#    ):
#        """
#        run the test ten times to be sure
#        """
#        area = example_area
#        oldpeople_household_sizes = {}
#        maxsize = 0
#        for household in area.households:
#            has_old_people = False
#            house_size = 0
#            for person in household.people:
#                house_size += 1
#                if person.age >= 65:
#                    has_old_people = True
#            if has_old_people:
#                if house_size not in oldpeople_household_sizes:
#                    oldpeople_household_sizes[house_size] = 0
#                oldpeople_household_sizes[house_size] += 1
#            if house_size > maxsize:
#                maxsize = house_size
#
#        # only the three generation family can have more than 3 people in it
#        big_houses = 0
#        for size in oldpeople_household_sizes.keys():
#            if size > 3:
#                big_houses += 1
#        assert big_houses <= 1
#
#    def test__kids_live_in_families(self, example_area):
#        area = example_area
#        kids_household_sizes = {}
#        for household in area.households:
#            has_kids = False
#            has_adults = False
#            house_size = 0
#            for person in household.people:
#                house_size += 1
#                if person.age <= 17:
#                    has_kids = True
#                else:
#                    has_adults = True
#            if has_kids:
#                assert has_adults
#                if house_size not in kids_household_sizes:
#                    kids_household_sizes[house_size] = 0
#                kids_household_sizes[house_size] += 1
#        # only big family is the multigenerational one
#        for size in kids_household_sizes.keys():
#            assert size <= 8
#
#    def test__most_couples_are_heterosexual(self, example_area):
#        different_sex = 0
#        total = 0
#        for household in example_area.households:
#            if len(household.people) == 2:
#                if household.people[0].sex != household.people[1].sex:
#                    different_sex += 1
#                    total += 1
#                else:
#                    total += 1
#
#        assert different_sex / total > 0.65
#
#    def test__household_size_is_acceptable(self, example_area):
#        for household in example_area.households:
#            size = len(household.people)
#            assert size <= 8


###class TestSpecificArea2:
###    """
###    Let's carefully check the first output area of the test set.
###    This area has no carehomes so we don't have to account for them.
###    The area E00062386 has this configuration:
###    0 0 0 0 1               9
###    0 0 0 1 0              11
###    0 0 0 0 2              20
###    0 0 0 2 0              29
###    1 0 >=0 2 0             5
###    >=2 0 >=0 2 0          12
###    0 0 >=1 2 0            13
###    1 0 >=0 1 0             6
###    >=2 0 >=0 1 0           2
###    0 0 >=1 1 0             0
###    1 0 >=0 >=1 >=0         1
###    >=2 0 >=0 >=1 >=0       0
###    0 >=1 0 0 0             0
###    0 0 0 0 >=2             1
###    0 0 >=0 >=0 >=0         1
###    >=0 >=0 >=0 >=0 >=0     0
###    Name: E00062386, dtype: int64
###    """
###    @pytest.fixture(name="example_area2", scope="module")
###    def make_geo(self):
###        geo = Geography.from_file({"oa": ["E00062386"]})
###        dem = Demography.for_geography(geo)
###        geo.areas[0].populate(dem)
###        return geo.areas[0]
###
###    @pytest.fixture(name="hd_area2", scope="module")
###    def populate_example_area(self, example_area2):
###        area = example_area2
###        household_distributor = HouseholdDistributor.from_file()
###        household_distributor.distribute_people_and_households_to_areas(
###            [area],
###        )
###        return household_distributor
###
###    def test__households_of_size1(self, hd_area2, example_area2):
###        area = example_area2
###        households_one = 0
###        for household in area.households:
###            if len(household.people) == 1:
###                households_one += 1
###        assert households_one == 20
