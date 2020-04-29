import numpy as np
import random
from scipy import stats
import warnings
from covid.groups.households import Household
from collections import OrderedDict

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""


class HouseholdError(BaseException):
    """ class for throwing household related errors """

    pass


def get_closest_element_in_array(array, value):
    min_idx = np.argmin(np.abs(value - array))
    return array[min_idx]


def normalize_probabilities_array(array):
    total_prob = sum(array)
    return np.array(array) / total_prob

def count_items_in_dict(dictionary):
    counter = 0
    for age in dictionary.keys():
        counter += len(dictionary[age])
    return counter

def count_remaining_people(dict1, dict2):
    return count_items_in_dict(dict1) + count_items_in_dict(dict2)


class HouseholdDistributor:
    """
    Contains routines to populate a given area with a realistic population with attributes based
    on census data from NOMIS. 
    """

    def __init__(
        self,
        first_kid_parent_age_differences,
        first_kid_parent_age_differences_probabilities,
        second_kid_parent_age_differences,
        second_kid_parent_age_differences_probabilities,
        couples_age_differences,
        couples_age_differences_probabilities,
        number_of_random_numbers=int(1e6),
    ):
        """
        Distribution_
        """
        self.STUDENT_MIN_AGE = 18
        self.STUDENT_MAX_AGE = 25
        self.OLD_MIN_AGE = 65
        self.OLD_MAX_AGE = 99
        self.ADULT_MIN_AGE = 18
        self.YOUNG_ADULT_MAX_AGE = 35
        self._first_kid_parent_age_diff_rv = stats.rv_discrete(
            values=(
                first_kid_parent_age_differences,
                first_kid_parent_age_differences_probabilities,
            ),
        )
        self._second_kid_parent_age_diff_rv = stats.rv_discrete(
            values=(
                second_kid_parent_age_differences,
                second_kid_parent_age_differences_probabilities,
            ),
        )
        self._couples_age_rv = stats.rv_discrete(
            values=(
                couples_age_differences,
                couples_age_differences_probabilities,
            )
        )
        self._random_sex_rv = stats.rv_discrete(values=((0, 1), (0.5, 0.5)))
        self._refresh_random_numbers_list(number_of_random_numbers)

    def _refresh_random_numbers_list(self, n=1000000):
        """
        Samples one million age differences for couples and parents-kids. Sampling in batches makes the code much faster. They are converted to lists so they can be popped.
        """
        # create one million random age difference array to save time
        self._couples_age_differences_list = list(self._couples_age_rv.rvs(size=n))
        self._first_kid_parent_age_diff_list = list(
            self._first_kid_parent_age_diff_rv.rvs(size=n)
        )
        self._second_kid_parent_age_diff_list = list(
            self._second_kid_parent_age_diff_rv.rvs(size=n)
        )
        self._random_sex_list = list(self._random_sex_rv.rvs(size=n))
        self._random_student_age = list(
            np.random.randint(self.STUDENT_MIN_AGE, self.STUDENT_MAX_AGE + 1, size=n)
        )
        self._random_oldpeople_age = list(
            np.random.randint(self.OLD_MIN_AGE, self.OLD_MAX_AGE + 1, size=n)
        )
        self._random_kid_age = list(np.random.randint(0, self.ADULT_MIN_AGE, size=n))
        siblings_age_gap1 = list(np.random.randint(-5, -2, size=n // 2))
        siblings_age_gap2 = list(np.random.randint(2, 5, size=n // 2))
        self._random_siblings_age_gap = siblings_age_gap1 + siblings_age_gap2
        random.shuffle(self._random_siblings_age_gap)
        self._random_adult_age = list(
            np.random.randint(self.ADULT_MIN_AGE, self.OLD_MIN_AGE, size=n)
        )
        self._random_youngpeople_age = list(
            np.random.randint(self.ADULT_MIN_AGE, self.YOUNG_ADULT_MAX_AGE + 1, size=n)
        )

    def distribute_people_to_households(
        self, area, number_households_per_composition: dict, n_students: int
    ):
        """
        Given a populated output area, it distributes the people to households. The instance of the Area class, area, should have two dictionary attributes, ``men_by_age`` and ``women_by_age``. The keys of the dictionaries are the ages and the values are the Person instances. The process of creating these dictionaries is done in people_distributor.py
        The ``number_households_per_composition`` argument is a dictionary containing the number of households per each composition. We obtain this from the nomis dataset and should be read by the inputs class in the world init.
        """
        households_with_extra_adults = []
        households_with_extra_oldpeople = []
        households_with_extra_kids = []
        households_with_extra_youngadults = []
        houses_with_kids = []

        # families with dependent kids
        key = "1 0 >=0 1 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_families_households(
                n_households=house_number,
                kids_per_house=1,
                parents_per_house=1,
                area=area,
                extra_people_lists=(households_with_extra_youngadults, houses_with_kids),
            )
    
        key = ">=2 0 >=0 1 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_families_households(
                n_households=house_number,
                kids_per_house=2,
                parents_per_house=1,
                area=area,
                extra_people_lists=(
                    households_with_extra_kids,
                    households_with_extra_youngadults,
                    houses_with_kids,
                ),
            )

        key = "1 0 >=0 2 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_families_households(
                n_households=house_number,
                kids_per_house=1,
                parents_per_house=2,
                area=area,
                extra_people_lists=(households_with_extra_youngadults, houses_with_kids),
            )

        key = ">=2 0 >=0 2 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_families_households(
                n_households=house_number,
                kids_per_house=2,
                parents_per_house=2,
                area=area,
                extra_people_lists=(
                    households_with_extra_youngadults,
                    households_with_extra_kids,
                    houses_with_kids,
                ),
            )

        # other household types
        # possible multigenerational, one kid
        key = "1 0 >=0 >=1 >=0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_families_households(
                n_households=house_number,
                kids_per_house=1,
                parents_per_house=1,
                area=area,
                extra_people_lists=(
                    households_with_extra_youngadults,
                    households_with_extra_adults,
                    households_with_extra_oldpeople,
                    houses_with_kids,
                ),
            )

        # possible multigenerational, two kids
        key = ">=2 0 >=0 >=1 >=0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_families_households(
                n_households=house_number,
                kids_per_house=2,
                parents_per_house=1,
                area=area,
                extra_people_lists=(
                    households_with_extra_kids,
                    households_with_extra_youngadults,
                    households_with_extra_adults,
                    households_with_extra_oldpeople,
                    houses_with_kids,
                ),
            )

        # all old people -> to be filled with remaining
        key = "0 0 0 0 >=2"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_oldpeople_households(
                people_per_household=2,
                n_households=house_number,
                area=area,
                extra_people_lists=(households_with_extra_oldpeople,),
            )

        # student households
        key = "0 >=1 0 0 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_all_student_households(
                area=area, n_students=n_students, student_houses_number=house_number,
            )

        # single person old
        key = "0 0 0 0 1"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_oldpeople_households(
                people_per_household=1, n_households=house_number, area=area,
            )

        # couples old
        key = "0 0 0 0 2"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_oldpeople_households(
                people_per_household=2, n_households=house_number, area=area,
            )

        # single person adult
        key = "0 0 0 1 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_nokids_households(
                adults_per_household=1, n_households=house_number, area=area,
            )

        # couple adult
        key = "0 0 0 2 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_nokids_households(
                adults_per_household=2, n_households=house_number, area=area,
            )

        key = "0 0 >=1 1 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_youngadult_with_parents_households(
                adults_per_household=1,
                n_households=house_number,
                area=area,
                extra_people_lists=(households_with_extra_youngadults,),
            )

        key = "0 0 >=1 2 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_youngadult_with_parents_households(
                adults_per_household=2,
                n_households=house_number,
                area=area,
                extra_people_lists=(households_with_extra_youngadults,),
            )


        # other trash -> to be filled with remaining
        key = "0 0 >=0 >=0 >=0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            for _ in range(house_number):
                household = self._create_household(area)
                households_with_extra_youngadults.append(household)
                households_with_extra_adults.append(household)
                households_with_extra_oldpeople.append(household)

        # print(number_households_per_composition)
        # we now fill the remaining ones
        for people_dict in [area.men_by_age, area.women_by_age]:
            for age in people_dict.keys():
                while people_dict[age]:
                    person = people_dict[age].pop()
                    if person.age < self.ADULT_MIN_AGE:
                        household = np.random.choice(households_with_extra_kids)
                        household.people.append(person)
                        continue
                    elif self.ADULT_MIN_AGE <= person.age <= self.YOUNG_ADULT_MAX_AGE:
                        household = np.random.choice(households_with_extra_youngadults)
                        household.people.append(person)
                        continue
                    elif self.ADULT_MIN_AGE <= person.age < self.OLD_MIN_AGE:
                        if households_with_extra_adults:
                            household = np.random.choice(households_with_extra_adults)
                        else:
                            household = np.random.choice(
                                households_with_extra_youngadults
                            )
                        household.people.append(person)
                        continue
                    elif self.OLD_MIN_AGE <= person.age:
                        if not households_with_extra_oldpeople:
                            household = self._create_household(area)
                            households_with_extra_oldpeople.append(household)
                            household.people.append(person)
                        else:
                            household = np.random.choice(households_with_extra_oldpeople)
                            household.people.append(person)
                        continue
                    print("woops")
                    print(person.age)


        assert count_remaining_people(area.men_by_age, area.women_by_age) == 0

    def _create_household(self, area):
        """Creates household in area and world."""
        household = Household()
        area.households.append(household)
        area.world.households.members.append(household)
        return household

    def _check_if_age_dict_is_empty(self, people_dict, age):
        """
        If the number of people in people_dict of the given age is 0, it deletes the key.
        """
        if len(people_dict[age]) == 0:
            del people_dict[age]

    def _get_closest_person_of_age(
        self, first_dict, second_dict, age, min_age=0, max_age=100
    ):
        """
        Tries to find the person with the closest age in first dict inside the min_age and max_age.
        If it fails, it looks into the second_dict. If it fails it returns None.
        """
        compatible_ages = np.array(list(first_dict.keys()))
        compatible_ages = compatible_ages[
            (min_age < compatible_ages) & (compatible_ages < max_age)
        ]
        if len(compatible_ages) == 0:
            compatible_ages = np.array(list(second_dict.keys()))
            compatible_ages = compatible_ages[
                (min_age < compatible_ages) & (compatible_ages < max_age)
            ]
            if len(compatible_ages) == 0:
                return None
            first_dict = second_dict
        closest_age = get_closest_element_in_array(compatible_ages, age)
        person = first_dict[closest_age].pop()
        self._check_if_age_dict_is_empty(first_dict, closest_age)
        return person

    def _get_matching_partner(self, person, area):
        """
        Given a person, it finds a suitable partner with similar age and opposite sex. The age difference is sampled from an observed distribution of age differences in couples in the US and the UK. More info in the data folder.
        """
        sex = int(not person.sex)  # get opposite sex
        sampled_age_difference = self._couples_age_differences_list.pop()
        target_age = person.age + sampled_age_difference
        if sex == 0:
            partner = self._get_closest_person_of_age(
                area.men_by_age,
                area.women_by_age,
                target_age,
                min_age=self.ADULT_MIN_AGE,
            )
            return partner
        else:
            partner = self._get_closest_person_of_age(
                area.women_by_age,
                area.men_by_age,
                target_age,
                min_age=self.ADULT_MIN_AGE,
            )
            return partner

    def _get_matching_parent(self, kid, area):
        """
        Given a person, it finds a suitable partner with similar age and opposite sex. The age difference is sampled from an observed distribution of age differences in couples in the US and the UK. More info in the data folder.
        """
        # first we try to find a mother, as it is more common to live with a single mother than a single father
        sampled_age_difference = self._first_kid_parent_age_diff_list.pop()
        target_age = kid.age + sampled_age_difference
        parent = self._get_closest_person_of_age(
            area.women_by_age,
            area.men_by_age,
            target_age,
            min_age=kid.age + self.ADULT_MIN_AGE,
            max_age=self.OLD_MIN_AGE,
        )
        return parent

    def _get_matching_second_kid(self, parent, area):
        """
        Given a person, it finds a suitable partner with similar age and opposite sex. The age difference is sampled from an observed distribution of age differences in couples in the US and the UK. More info in the data folder.
        """
        # first we try to find a mother, as it is more common to live with a single mother than a single father
        sampled_age_difference = self._second_kid_parent_age_diff_list.pop()
        target_age = parent.age - sampled_age_difference
        kid_sex = self._random_sex_list.pop()
        if kid_sex == 0:
            kid = self._get_closest_person_of_age(
                area.men_by_age,
                area.women_by_age,
                target_age,
                min_age=0,
                max_age=self.ADULT_MIN_AGE-1,
            )
        else:
            kid = self._get_closest_person_of_age(
                area.women_by_age,
                area.men_by_age,
                target_age,
                min_age=0,
                max_age=self.ADULT_MIN_AGE-1,
            )
        return kid  

    def fill_all_student_households(
        self, area, n_students: int, student_houses_number: int
    ):
        if n_students == 0:
            return None
        # students per household
        ratio = np.floor(n_students / student_houses_number)
        # get all people in the students age
        # fill students to households
        students_left = True
        while students_left:
            household = self._create_household(area)
            student_houses_number -= 1
            for _ in range(0, np.floor(ratio)):
                sex = self._random_sex_list.pop()
                if sex == 0:
                    age = self._random_student_age.pop()
                    student = self._get_closest_person_of_age(
                        area.men_by_age,
                        area.women_by_age,
                        age,
                        min_age=self.STUDENT_MIN_AGE,
                        max_age=self.STUDENT_MAX_AGE,
                    )
                else:
                    age = self._random_student_age.pop()
                    student = self._get_closest_person_of_age(
                        area.women_by_age,
                        area.men_by_age,
                        age,
                        min_age=self.STUDENT_MIN_AGE,
                        max_age=self.STUDENT_MAX_AGE,
                    )
                if student is None:
                    return None
                household.people.append(student)
                n_students -= 1
                if n_students == 0 or student_houses_number == 0:
                    return None

    def fill_oldpeople_households(
        self, people_per_household, n_households, area, extra_people_lists=()
    ):

        for _ in range(0, n_households):
            household = self._create_household(area)
            age = self._random_oldpeople_age.pop()
            sex = self._random_sex_list.pop()
            if sex == 0:
                person = self._get_closest_person_of_age(
                    area.men_by_age, area.women_by_age, age, min_age=self.OLD_MIN_AGE
                )
            else:
                person = self._get_closest_person_of_age(
                    area.women_by_age, area.men_by_age, age, min_age=self.OLD_MIN_AGE
                )
            if person is None:
                return None
            household.people.append(person)
            for array in extra_people_lists:
                array.append(household)
            if people_per_household == 1:
                continue
            else:
                partner = self._get_matching_partner(person, area)
                if partner is None:
                    return None
                household.people.append(partner)

    def fill_families_households(
        self,
        n_households: int,
        kids_per_house: int,
        parents_per_house: int,
        area,
        extra_people_lists=(),
    ):
        for _ in range(0, n_households):
            household = self._create_household(area)
            first_kid_age = self._random_kid_age.pop()
            first_kid_sex = self._random_sex_list.pop()
            if first_kid_sex == 0:
                first_kid = self._get_closest_person_of_age(
                    area.men_by_age,
                    area.women_by_age,
                    first_kid_age,
                    min_age=0,
                    max_age=self.ADULT_MIN_AGE - 1,
                )
            else:
                first_kid = self._get_closest_person_of_age(
                    area.women_by_age,
                    area.men_by_age,
                    first_kid_age,
                    min_age=0,
                    max_age=self.ADULT_MIN_AGE - 1,
                )
            if first_kid is None:
                return None
            household.people.append(first_kid)
            first_parent = self._get_matching_parent(first_kid, area)
            if first_parent is None:
                raise ValueError("Orphan kid")
            for array in extra_people_lists:
                array.append(household)
            household.people.append(first_parent)
            if parents_per_house == 2:
                second_parent = self._get_matching_partner(first_parent, area)
                if second_parent is None:
                    return None
                household.people.append(second_parent)

            if kids_per_house == 2:
                second_kid = self._get_matching_second_kid(first_parent, area)
                if second_kid is None:
                    return None
                household.people.append(second_kid)

    def fill_nokids_households(
        self, adults_per_household, n_households, area, extra_people_lists=(),
    ):
        for _ in range(0, n_households):
            household = self._create_household(area)
            first_adult_sex = self._random_sex_list.pop()
            first_adult_age = self._random_adult_age.pop()
            if first_adult_sex == 0:
                first_adult = self._get_closest_person_of_age(
                    area.men_by_age,
                    area.women_by_age,
                    first_adult_age,
                    min_age=18,
                    max_age=65,
                )
            else:
                first_adult = self._get_closest_person_of_age(
                    area.women_by_age,
                    area.men_by_age,
                    first_adult_age,
                    min_age=18,
                    max_age=65,
                )
            if first_adult is None:
                return None
            household.people.append(first_adult)
            for array in extra_people_lists:
                array.append(household)
            if adults_per_household == 1:
                continue
            second_adult = self._get_matching_partner(first_adult, area)
            if second_adult is None:
                return None
            household.people.append(second_adult)

    def fill_youngadult_households(
        self, youngadults_per_household, n_households, area, extra_people_lists=()
    ):
        for _ in range(0, n_households):
            household = self._create_household(area)
            for _ in youngadults_per_household:
                age = self._random_youngpeople_age.pop()
                sex = self._random_sex_list.pop()
                if sex == 0:
                    person = self._get_closest_person_of_age(
                        area.men_by_age,
                        area.women_by_age,
                        age,
                        min_age=self.ADULT_MIN_AGE,
                        max_age=self.YOUNG_ADULT_MAX_AGE,
                    )
                else:
                    person = self._get_closest_person_of_age(
                        area.women_by_age,
                        area.men_by_age,
                        age,
                        min_age=self.ADULT_MIN_AGE,
                        max_age=self.YOUNG_ADULT_MAX_AGE,
                    )
                if person is None:
                    return None
                household.people.append(person)
            for array in extra_people_lists:
                array.append(household)

    def fill_youngadult_with_parents_households(
        self, adults_per_household, n_households, area, extra_people_lists=()
    ):
        for _ in range(0, n_households):
            household = self._create_household(area)
            for array in extra_people_lists:
                array.append(household)
            youngadult_sex = self._random_sex_list.pop()
            youngadult_age = self._random_youngpeople_age.pop()
            if youngadult_sex == 0:
                youngadult = self._get_closest_person_of_age(
                    area.men_by_age,
                    area.women_by_age,
                    youngadult_age,
                    self.OLD_MIN_AGE,
                    self.YOUNG_ADULT_MAX_AGE,
                )
            else:
                youngadult = self._get_closest_person_of_age(
                    area.women_by_age,
                    area.men_by_age,
                    youngadult_age,
                    self.OLD_MIN_AGE,
                    self.YOUNG_ADULT_MAX_AGE,
                )
            if youngadult is None:
                return None
            household.people.append(youngadult)
            adult = self._get_matching_parent(youngadult, area)
            if adult is None:
                return None
            household.people.append(adult)
            if adults_per_household == 1:
                continue
            else:
                adult2 = self._get_matching_partner(adult, area)
                if adult2 is None:
                    return None
                household.people.append(adult2)
