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

class HouseholdDistributor:
    """
    Contains routines to populate a given area with a realistic population with attributes based
    on census data from NOMIS. 
    """

    def __init__(
        self,
        distribution_kids_parents_age: dict = None,
        distribution_couples_age: dict = None,
        number_of_random_numbers=int(1e6),
    ):
        self.STUDENT_MIN_AGE = 18
        self.STUDENT_MAX_AGE = 25
        self.OLD_MIN_AGE = 65
        self.OLD_MAX_AGE = 99
        self.ADULT_MIN_AGE = 18
        self.YOUNG_ADULT_MAX_AGE = 35
        self._kids_parents_age_rv = stats.rv_discrete(
            values=(
                list(distribution_kids_parents_age.keys()),
                list(distribution_kids_parents_age.values()),
            ),
        )
        self._couples_age_rv = stats.rv_discrete(
            values=(
                list(distribution_couples_age.keys()),
                list(distribution_couples_age.values()),
            )
        )
        self._random_sex_rv = stats.rv_discrete(values=((0, 1), (0.5, 0.5)))
        # self._refresh_random_numbers_list(number_of_random_numbers)

    def _refresh_random_numbers_list(self, n=1000000):
        """
        Samples one million age differences for couples and parents-kids. Sampling in batches makes the code much faster. They are converted to lists so they can be popped.
        """
        # create one million random age difference array to save time
        print(n)
        test = self._couples_age_rv.rvs(size=n)
        print(test)
        self._couples_age_differences_list = list(self._couples_age_rv.rvs(size=n))
        # create one million random age difference array to save time
        self._kids_parents_age_differences_list = list(
            self._kids_parents_age_rv.rvs(size=n)
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

        # single adult with possible young adults
        key = "0 0 >=0 1 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_nokids_households(
                adults_per_household=1, n_households=house_number, area=area,
            )

        # couple  with possible young adults
        key = "0 0 >=0 2 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_nokids_households(
                adults_per_household=2,
                n_households=house_number,
                area=area,
                extra_people_lists=(households_with_extra_youngadults),
            )

        key = "0 0 >=1 1 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_youngadult_with_parents_households(
                adults_per_household=1,
                n_households=house_number,
                area=area,
                extra_people_lists=(households_with_extra_youngadults),
            )

        key = "0 0 >=1 2 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_youngadult_with_parents_households(
                adults_per_household=2,
                n_households=house_number,
                area=area,
                extra_people_lists=(households_with_extra_youngadults),
            )

        # families with dependent kids
        key = "1 0 >=0 1 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_families_households(
                n_households=house_number,
                kids_per_house=1,
                parents_per_house=1,
                area=area,
                extra_people_lists=(households_with_extra_youngadults),
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
                extra_people_lists=(households_with_extra_youngadults),
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
                ),
            )

        # all old people -> to be filled with remaining
        key = "0 0 0 0 >=1"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_oldpeople_households(
                people_per_household=1,
                n_households=house_number,
                area=area,
                extra_people_lists=(households_with_extra_oldpeople),
            )

        # other trash -> to be filled with remaining
        key = "0 0 >=1 >=0 >=0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            self.fill_youngadult_households(
                youngadults_per_household=1,
                n_households=house_number,
                area=area,
                extra_people_lists=(
                    households_with_extra_youngadults,
                    households_with_extra_adults,
                    households_with_extra_oldpeople,
                ),
            )

        # we now fill the remaining ones
        for people_dict in [area.men_by_age, area.women_by_age]:
            for age in people_dict.keys():
                for person in people_dict[age]:
                    if person.age < self.ADULT_MIN_AGE:
                        kid = people_dict[person.age].pop()
                        household = np.random.choice(households_with_extra_kids)
                        household.people.append(kid)
                    if self.ADULT_MIN_AGE <= person.age <= self.YOUNG_ADULT_MAX_AGE:
                        youngadult = people_dict[person.age].pop()
                        household = np.random.choice(households_with_extra_youngadults)
                        household.people.append(youngadult)
                    if self.YOUNG_ADULT_MAX_AGE < person.age <= self.OLD_MIN_AGE:
                        adult = people_dict[person.age].pop()
                        household = np.random.choice(households_with_extra_adults)
                        household.people.append(adult)
                    if self.OLD_MIN_AGE <= person.age:
                        old = people_dict[person.age].pop()
                        household = np.random.choice(households_with_extra_oldpeople)
                        household.people.append(old)

    def _create_household(self, area):
        """Creates household in area and world."""
        household = Household()
        area.households.append(household)
        area.world.households.append(household)
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
        compatible_ages = np.array(first_dict.keys())
        compatible_ages = compatible_ages[
            (min_age < compatible_ages) & (compatible_ages < max_age)
        ]
        if len(compatible_ages) == 0:
            compatible_ages = np.array(second_dict.keys())
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
        sampled_age_difference = self._kids_parents_age_differences_list.pop()
        target_age = kid.age + sampled_age_difference
        parent = self._get_closest_person_of_age(
            area.women_by_age,
            area.men_by_age,
            target_age,
            min_age=kid.age + self.ADULT_MIN_AGE,
            max_age=self.OLD_MIN_AGE,
        )
        return parent

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
                    print("this should not happen... I ran out of students!")
                    students_left = False
                    break
                household.people.append(student)
                n_students -= 1
                if n_students == 0 or student_houses_number == 0:
                    students_left = False
                    break

    def fill_oldpeople_households(
        self, people_per_household, n_households, area, extra_people_lists=()
    ):

        for _ in range(0, n_households):
            household = self._create_household(area)
            for array in extra_people_lists:
                array.append(household)
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
                print("This shouldn't happen, I ran out of old people!")
                return None
            household.people.append(person)
            if people_per_household == 1:
                continue
            else:
                partner = self._get_matching_partner(person, area)
                if partner is not None:
                    household.people.append(partner)
                else:
                    print(
                        "This shouldn't happen, I ran out of old people! (second old)"
                    )
                    return None

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
                print("prolem! ran out of kids!")
                return None
            household.people.append(first_kid)
            first_parent = self._get_matching_parent(first_kid, area)
            household.people.append(first_parent)
            if parents_per_house == 2:
                second_parent = self._get_matching_partner(first_parent, area)
                if second_parent is not None:
                    household.people.append(second_parent)

            if kids_per_house == 2:
                second_kid_age = first_kid.age + self._random_siblings_age_gap.pop()
                second_kid_sex = self._random_sex_list.pop()
                if second_kid_sex == 0:
                    second_kid = self._get_closest_person_of_age(
                        area.men_by_age,
                        area.women_by_age,
                        second_kid_age,
                        min_age=0,
                        max_age=self.ADULT_MIN_AGE - 1,
                    )
                else:
                    second_kid = self._get_closest_person_of_age(
                        area.women_by_age,
                        area.men_by_age,
                        second_kid_age,
                        min_age=0,
                        max_age=self.ADULT_MIN_AGE - 1,
                    )
                household.people.append(second_kid)
            for array in extra_people_lists:
                array.append(household)

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
                household.people.append(first_adult)
            for array in extra_people_lists:
                array.append(household)
            if adults_per_household == 1:
                continue
            second_adult = self._get_matching_partner(first_adult, area)
            household.people.append(second_adult)

    def fill_youngadult_households(
        self, youngadults_per_household, n_households, area, extra_people_lists=()
    ):
        for _ in range(0, n_households):
            household = self._create_household(area)
            for array in extra_people_lists:
                array.append(household)
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
                household.people.append(person)

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

            household.people.append(youngadult)
            adult = self._get_matching_parent(youngadult, area)
            household.people.append(adult)
            if adults_per_household == 1:
                continue
            else:
                adult2 = self._get_matching_partner(adult, area)
                household.people.append(adult2)
