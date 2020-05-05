import numpy as np
import random
from scipy import stats
import warnings
from covid.groups.households import Household
from collections import OrderedDict
from covid.groups import Person
from covid.groups import Area

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""

ALLOWED_HOUSEHOLD_COMPOSITIONS = [
    "1 0 >=0 1 0",
    ">=2 0 >=0 1 0",
    "1 0 >=0 2 0",
    ">=2 0 >=0 2 0",
    "1 0 >=0 >=1 >=0",
    ">=2 0 >=0 >=1 >=0",
    "0 0 0 0 >=2",
    "0 >=1 0 0 0",
    "0 0 0 0 1",
    "0 0 0 0 2",
    "0 0 0 1 0",
    "0 0 0 2 0",
    "0 0 >=1 1 0",
    "0 0 >=1 2 0",
    "0 0 >=0 >=0 >=0",
    ">=0 >=0 >=0 >=0 >=0",
]


class HouseholdError(BaseException):
    """ class for throwing household related errors """

    pass


def get_closest_element_in_array(array, value):
    min_idx = np.argmin(np.abs(value - array))
    return array[min_idx]


def count_items_in_dict(dictionary):
    counter = 0
    for age in dictionary.keys():
        counter += len(dictionary[age])
    return counter


def get_number_of_kids(dict1, dict2):
    kids_total = 0
    for d in [dict1, dict2]:
        for age in range(0, 18):
            if age in d:
                kids_total += len(d[age])
    return kids_total


def count_remaining_people(dict1, dict2):
    return count_items_in_dict(dict1) + count_items_in_dict(dict2)


class HouseholdDistributor:
    """
    Contains routines to populate a given area with a realistic population with attributes based
    on census data from NOMIS. 
    """

    def __init__(
        self,
        first_kid_parent_age_differences: list,
        first_kid_parent_age_differences_probabilities: list,
        second_kid_parent_age_differences: list,
        second_kid_parent_age_differences_probabilities: list,
        couples_age_differences: list,
        couples_age_differences_probabilities: list,
        number_of_random_numbers=int(1e6),
    ):
        """
        Distribution
        """
        self.KID_MAX_AGE = 17
        self.STUDENT_MIN_AGE = 18
        self.STUDENT_MAX_AGE = 25
        self.OLD_MIN_AGE = 65
        self.OLD_MAX_AGE = 99
        self.ADULT_MIN_AGE = 18
        self.ADULT_MAX_AGE = 64
        self.YOUNG_ADULT_MIN_AGE = 18
        self.YOUNG_ADULT_MAX_AGE = 35
        self.MAX_AGE_TO_BE_PARENT = 64
        self.MAX_HOUSEHOLD_SIZE = 8

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
            values=(couples_age_differences, couples_age_differences_probabilities,)
        )
        self._random_sex_rv = stats.rv_discrete(values=((0, 1), (0.5, 0.5)))
        self._refresh_random_numbers_list(number_of_random_numbers)

    @classmethod
    def from_inputs(cls, inputs):
        n_people = inputs.n_residents.values.sum()
        kids_parents_age_diff_1 = inputs.parent_child_df["0"]
        kids_parents_age_diff_2 = inputs.parent_child_df["1"]
        couples_age_diff = inputs.husband_wife_df
        first_kid_parent_age_differences = (
            np.array(kids_parents_age_diff_1.index).flatten(),
        )
        first_kid_parent_age_differences_probabilities = (
            np.array(kids_parents_age_diff_1.values).flatten(),
        )
        second_kid_parent_age_differences = (
            np.array(kids_parents_age_diff_2.index).flatten(),
        )
        second_kid_parent_age_differences_probabilities = (
            np.array(kids_parents_age_diff_2.values).flatten(),
        )
        couples_age_differences = np.array(couples_age_diff.index).flatten()
        couples_age_differences_probabilities = np.array(
            couples_age_diff.values
        ).flatten()
        return cls(
            first_kid_parent_age_differences,
            first_kid_parent_age_differences_probabilities,
            second_kid_parent_age_differences,
            second_kid_parent_age_differences_probabilities,
            couples_age_differences,
            couples_age_differences_probabilities,
            number_of_random_numbers=n_people,
        )

    def _refresh_random_numbers_list(self, n=1000000) -> None:
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
        self._random_age = list(np.random.randint(0, 99, size=n))
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
        self,
        area: Area,
        number_households_per_composition: dict,
        n_students: int,
        n_people_in_communal: int,
    ) -> None:
        """
        Given a populated output area, it distributes the people to households. The instance of the Area class, area, should have two dictionary attributes, ``men_by_age`` and ``women_by_age``. The keys of the dictionaries are the ages and the values are the Person instances. The process of creating these dictionaries is done in people_distributor.py
        The ``number_households_per_composition`` argument is a dictionary containing the number of households per each composition. We obtain this from the nomis dataset and should be read by the inputs class in the world init.
        """
        households_with_extra_adults = []
        households_with_extra_oldpeople = []
        households_with_extra_kids = []
        households_with_extra_youngadults = []
        households_with_kids = []
        if not area.men_by_age and not area.women_by_age:
            raise HouseholdError("No people in Area!")
        total_number_of_households = 0
        for key in number_households_per_composition:
            total_number_of_households += number_households_per_composition[key]
            if key not in ALLOWED_HOUSEHOLD_COMPOSITIONS:
                raise HouseholdError(f"Household composition {key} not supported")

        # student households
        key = "0 >=1 0 0 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                self.fill_all_student_households(
                    area=area,
                    n_students=n_students,
                    student_houses_number=house_number,
                )

        # single person old
        key = "0 0 0 0 1"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                self.fill_oldpeople_households(
                    people_per_household=1,
                    n_households=house_number,
                    max_household_size=1,
                    extra_people_lists=(
                        households_with_extra_adults,
                        households_with_extra_oldpeople,
                    ),
                    area=area,
                )

        # couples old
        key = "0 0 0 0 2"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                self.fill_oldpeople_households(
                    people_per_household=2,
                    n_households=house_number,
                    max_household_size=2,
                    extra_people_lists=(
                        households_with_extra_adults,
                        households_with_extra_oldpeople,
                    ),
                    area=area,
                )

        # other household types -> old houses with possibly more old people
        key = "0 0 0 0 >=2"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                self.fill_oldpeople_households(
                    people_per_household=2,
                    n_households=house_number,
                    area=area,
                    extra_people_lists=(households_with_extra_oldpeople,),
                )

        # possible multigenerational, one kid
        key = "1 0 >=0 >=1 >=0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                self.fill_families_households(
                    n_households=house_number,
                    kids_per_house=1,
                    parents_per_house=1,
                    old_per_house=1,
                    extra_people_lists=(
                        households_with_kids,
                        households_with_extra_youngadults,
                        households_with_extra_adults,
                    ),
                    area=area,
                )
        # possible multigenerational, two kids we limit number of old people to 1.
        key = ">=2 0 >=0 >=1 >=0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                self.fill_families_households(
                    n_households=house_number,
                    kids_per_house=2,
                    parents_per_house=1,
                    old_per_house=1,
                    area=area,
                    extra_people_lists=(
                        households_with_extra_kids,
                        households_with_kids,
                        households_with_extra_youngadults,
                        households_with_extra_adults,
                    ),
                )

        # now we fill families to make sure we don't have orphan kids at the end.
        # families with dependent kids
        key = "1 0 >=0 1 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                self.fill_families_households(
                    n_households=house_number,
                    kids_per_house=1,
                    parents_per_house=1,
                    old_per_house=0,
                    area=area,
                    extra_people_lists=(
                        households_with_kids,
                        households_with_extra_youngadults,
                    ),
                )

        key = ">=2 0 >=0 1 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                self.fill_families_households(
                    n_households=house_number,
                    kids_per_house=2,
                    parents_per_house=1,
                    old_per_house=0,
                    area=area,
                    extra_people_lists=(
                        households_with_extra_kids,
                        households_with_kids,
                        households_with_extra_youngadults,
                    ),
                )

        key = "1 0 >=0 2 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                self.fill_families_households(
                    n_households=house_number,
                    kids_per_house=1,
                    parents_per_house=2,
                    old_per_house=0,
                    area=area,
                    extra_people_lists=(
                        households_with_kids,
                        households_with_extra_youngadults,
                    ),
                )

        key = ">=2 0 >=0 2 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                self.fill_families_households(
                    n_households=house_number,
                    kids_per_house=2,
                    parents_per_house=2,
                    old_per_house=0,
                    area=area,
                    extra_people_lists=(
                        households_with_kids,
                        households_with_extra_kids,
                        households_with_extra_youngadults,
                    ),
                )
        # couple adult, it's possible to have a person < 65 with one > 65
        key = "0 0 0 2 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                self.fill_nokids_households(
                    adults_per_household=2,
                    n_households=house_number,
                    max_household_size=2,
                    area=area,
                    extra_people_lists=(
                        households_with_extra_adults,
                        households_with_extra_oldpeople,
                    ),
                )

        key = "0 0 >=1 1 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                self.fill_youngadult_with_parents_households(
                    adults_per_household=1,
                    n_households=house_number,
                    area=area,
                    extra_people_lists=(households_with_extra_youngadults,),
                )

        key = "0 0 >=1 2 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                self.fill_youngadult_with_parents_households(
                    adults_per_household=2,
                    n_households=house_number,
                    area=area,
                    extra_people_lists=(households_with_extra_youngadults,),
                )

        # single person adult
        key = "0 0 0 1 0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                self.fill_nokids_households(
                    adults_per_household=1,
                    n_households=house_number,
                    max_household_size=1,
                    area=area,
                )

        # other trash -> to be filled with remaining
        key = "0 0 >=0 >=0 >=0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            if house_number > 0:
                for _ in range(house_number):
                    household = self._create_household(area)
                    households_with_extra_youngadults.append(household)
                    households_with_extra_adults.append(household)
                    households_with_extra_oldpeople.append(household)

        # we have so far filled the minimum household configurations.
        # The rest are then distributed randomly between the houses that
        # accept their characteristics, or we put them in a communal building.

        remaining_people = count_remaining_people(area.men_by_age, area.women_by_age)
        # check if they fit in communal spaces
        communal_houses = 0
        key = ">=0 >=0 >=0 >=0 >=0"
        if key in number_households_per_composition:
            house_number = number_households_per_composition[key]
            communal_houses = house_number
            if n_people_in_communal >= 0 and house_number > 0:
                # if house_number > 0 and n_people_in_communal > 0:
                # if remaining_people > n_people_in_communal:
                # n_to_fill = remaining_people - n_people_in_communal
                to_fill_in_communal = min(n_people_in_communal, remaining_people)
                self.fill_all_communal_establishments(
                    n_establishments=house_number,
                    n_people_in_communal=to_fill_in_communal,
                    area=area,
                )
                # self.fill_random_people_to_existing_households(
                #    households_with_extra_kids,
                #    households_with_kids,
                #    households_with_extra_youngadults,
                #    households_with_extra_adults,
                #    households_with_extra_oldpeople,
                #    area=area,
                # )

        # remaining
        self.fill_random_people_to_existing_households(
            households_with_extra_kids,
            households_with_kids,
            households_with_extra_youngadults,
            households_with_extra_adults,
            households_with_extra_oldpeople,
            area=area,
        )

        # append to world
        total_people = 0
        for household in area.households:
            area.world.households.members.append(household)
            total_people += household.size
        # try:
        #    assert (
        #        total_number_of_households - communal_houses
        #        <= len(area.households)
        #        <= total_number_of_households
        #    )
        # except:
        #    raise HouseholdError("Number of households does not match.")
        # try:
        #    assert total_people == area.n_residents
        # except:
        #    raise HouseholdError(
        #        f"Number of people in households {total_people} does not match number of people in area {area.n_residents}"
        #    )
        ## destroy any empty houses
        # area.households = [
        #    household for household in area.households if household.size > 0
        # ]

    def _create_household(
        self, area: Area, communal=False, max_household_size=np.inf
    ) -> Household:
        """Creates household in area and world."""
        household = Household(communal=communal, max_size=max_household_size)
        area.households.append(household)
        # area.world.households.members.append(household)
        return household

    def _check_if_age_dict_is_empty(self, people_dict: dict, age: int) -> bool:
        """
        If the number of people in people_dict of the given age is 0, it deletes the key.
        """
        ret = False
        if len(people_dict[age]) == 0:
            ret = True
            del people_dict[age]
        return ret

    def _check_if_oldpeople_left(self, area: Area) -> bool:
        ret = False
        for age in range(65, 100):
            if age in area.women_by_age or age in area.men_by_age:
                ret = True
                break
        return ret

    def _count_oldpeople_left(self, area: Area) -> int:
        ret = 0
        for age in range(65, 100):
            if age in area.women_by_age:
                ret += len(area.women_by_age[age])
            if age in area.men_by_age:
                ret += len(area.men_by_age[age])
        return ret

    def _get_closest_person_of_age(
        self, first_dict: dict, second_dict: dict, age: int, min_age=0, max_age=100
    ) -> Person:
        """
        Tries to find the person with the closest age in first dict inside the min_age and max_age.
        If it fails, it looks into the second_dict. If it fails it returns None.
        """
        if age < min_age or age > max_age:
            return None

        compatible_ages = np.array(list(first_dict.keys()))
        compatible_ages = compatible_ages[
            (min_age <= compatible_ages) & (compatible_ages <= max_age)
        ]
        if len(compatible_ages) == 0:
            compatible_ages = np.array(list(second_dict.keys()))
            compatible_ages = compatible_ages[
                (min_age <= compatible_ages) & (compatible_ages <= max_age)
            ]
            if len(compatible_ages) == 0:
                return None
            first_dict = second_dict
        closest_age = get_closest_element_in_array(compatible_ages, age)
        person = first_dict[closest_age].pop()
        self._check_if_age_dict_is_empty(first_dict, closest_age)
        return person

    def _get_random_person_in_age_bracket(
        self, area: Area, min_age=0, max_age=100
    ) -> Person:
        sex = self._random_sex_list.pop()
        age = np.random.randint(min_age, max_age + 1)
        if sex == 0:
            person = self._get_closest_person_of_age(
                area.men_by_age, area.women_by_age, age, min_age, max_age
            )
        else:
            person = self._get_closest_person_of_age(
                area.women_by_age, area.men_by_age, age, min_age, max_age
            )
        return person

    def _get_matching_partner(
        self, person: Person, area: Area, under_65=False, over_65=False
    ) -> Person:
        """
        Given a person, it finds a suitable partner with similar age and opposite sex. The age difference is sampled from an observed distribution of age differences in couples in the US and the UK. More info in the data folder.
        """
        sex = int(not person.sex)  # get opposite sex
        sampled_age_difference = self._couples_age_differences_list.pop()
        if under_65:
            target_age = min(person.age - abs(sampled_age_difference), 64)
        else:
            target_age = person.age + sampled_age_difference
        if over_65:
            target_age = max(65, target_age)
        target_age = max(min(self.OLD_MAX_AGE, target_age), 18)
        if sex == 0:
            partner = self._get_closest_person_of_age(
                area.men_by_age,
                area.women_by_age,
                target_age,
                min_age=self.ADULT_MIN_AGE,
            )
            if partner is None:
                print("failed")
                print(f"target age: {target_age}")
                print(area.men_by_age.keys())
                print(area.women_by_age.keys())
            return partner
        else:
            partner = self._get_closest_person_of_age(
                area.women_by_age,
                area.men_by_age,
                target_age,
                min_age=self.ADULT_MIN_AGE,
            )
            if partner is None:
                print("failed")
                print(f"target age: {target_age}")
                print(area.men_by_age.keys())
                print(area.women_by_age.keys())
            return partner

    def _get_matching_parent(self, kid: Person, area: Area) -> Person:
        """
        Given a person, it finds a suitable partner with similar age and opposite sex. The age difference is sampled from an observed distribution of age differences in couples in the US and the UK. More info in the data folder.
        """
        # first we try to find a mother, as it is more common to live with a single mother than a single father
        sampled_age_difference = self._first_kid_parent_age_diff_list.pop()
        target_age = max(
            min(kid.age + sampled_age_difference, self.MAX_AGE_TO_BE_PARENT),
            self.ADULT_MIN_AGE,
        )
        parent = self._get_closest_person_of_age(
            area.women_by_age,
            area.men_by_age,
            target_age,
            min_age=self.ADULT_MIN_AGE,
            max_age=self.MAX_AGE_TO_BE_PARENT,
        )
        return parent

    def _get_matching_second_kid(self, parent: Person, area: Area) -> Person:
        """
        Given a person, it finds a suitable partner with similar age and opposite sex. The age difference is sampled from an observed distribution of age differences in couples in the US and the UK. More info in the data folder.
        """
        # first we try to find a mother, as it is more common to live with a single mother than a single father
        sampled_age_difference = self._second_kid_parent_age_diff_list.pop()
        target_age = min(max(parent.age - sampled_age_difference, 0), self.KID_MAX_AGE)
        kid_sex = self._random_sex_list.pop()
        if kid_sex == 0:
            kid = self._get_closest_person_of_age(
                area.men_by_age,
                area.women_by_age,
                target_age,
                min_age=0,
                max_age=self.KID_MAX_AGE,
            )
        else:
            kid = self._get_closest_person_of_age(
                area.women_by_age,
                area.men_by_age,
                target_age,
                min_age=0,
                max_age=self.KID_MAX_AGE,
            )
        return kid

    def fill_all_student_households(
        self, area: Area, n_students: int, student_houses_number: int
    ) -> None:
        if n_students == 0:
            return None
        # students per household
        ratio = max(int(n_students / student_houses_number), 1)
        # get all people in the students age
        # fill students to households
        students_left = n_students
        student_houses = []
        for _ in range(0, student_houses_number):
            household = self._create_household(area)
            student_houses.append(household)
            for _ in range(0, ratio):
                student = self._get_random_person_in_age_bracket(
                    area, min_age=self.STUDENT_MIN_AGE, max_age=self.STUDENT_MAX_AGE
                )
                if student is None:
                    raise HouseholdError("Students do not match!")
                household.people.append(student)
                students_left -= 1
        assert students_left >= 0
        index = 0
        while students_left:
            household = student_houses[index]
            student = self._get_random_person_in_age_bracket(
                area, min_age=self.STUDENT_MIN_AGE, max_age=self.STUDENT_MAX_AGE
            )
            household.people.append(student)
            students_left -= 1
            index += 1
            index = index % len(student_houses)

    def fill_oldpeople_households(
        self,
        people_per_household: int,
        n_households: int,
        area: Area,
        extra_people_lists=(),
        max_household_size=np.inf,
    ) -> None:
        for i in range(0, n_households):
            household = self._create_household(
                area, max_household_size=max_household_size
            )
            person = self._get_random_person_in_age_bracket(
                area, min_age=self.OLD_MIN_AGE, max_age=self.OLD_MAX_AGE
            )
            if person is None:
                # no old people left, leave the house and the rest empty and adults can come here later.
                for array in extra_people_lists:
                    array.append(household)
                for _ in range(i + 1, n_households):
                    household = self._create_household(
                        area, max_household_size=max_household_size
                    )
                    for array in extra_people_lists:
                        array.append(household)
                return None
            household.people.append(person)
            if people_per_household > 1 and person is not None:
                partner = self._get_matching_partner(person, area, over_65=True)
                # if partner is None:
                #    partner = self._get_matching_partner(person, area, under_65=True)
                if partner is not None:
                    household.people.append(partner)
            if household.size < household.max_size:
                for array in extra_people_lists:
                    array.append(household)

    def fill_families_households(
        self,
        n_households: int,
        kids_per_house: int,
        parents_per_house: int,
        old_per_house: int,
        area: Area,
        max_household_size=np.inf,
        extra_people_lists=(),
    ) -> None:
        for i in range(0, n_households):
            household = self._create_household(
                area, max_household_size=max_household_size
            )
            first_kid = self._get_random_person_in_age_bracket(
                area, min_age=0, max_age=self.KID_MAX_AGE
            )
            if first_kid is None:
                # fill with young adult instead
                first_kid = self._get_random_person_in_age_bracket(
                    area,
                    min_age=self.YOUNG_ADULT_MIN_AGE,
                    max_age=self.YOUNG_ADULT_MAX_AGE,
                )
                if first_kid is None:
                    for array in extra_people_lists:
                        array.append(household)
                    for _ in range(i + 1, n_households):
                        household = self._create_household(
                            area, max_household_size=max_household_size
                        )
                        for array in extra_people_lists:
                            array.append(household)
                    return None
            household.people.append(first_kid)
            first_parent = self._get_matching_parent(first_kid, area)
            if first_parent is None:
                raise HouseholdError(
                    "Orphan kid. Check household configuration and population."
                )
            household.people.append(first_parent)
            for array in extra_people_lists:
                array.append(household)
            if old_per_house > 0:
                for _ in range(old_per_house):
                    random_old = self._get_random_person_in_age_bracket(
                        area, min_age=self.OLD_MIN_AGE, max_age=self.OLD_MAX_AGE
                    )
                    if random_old is None:
                        break
                    household.people.append(random_old)

            if parents_per_house == 2 and first_parent is not None:
                second_parent = self._get_matching_partner(first_parent, area)
                if second_parent is not None:
                    # return None
                    household.people.append(second_parent)

            if kids_per_house == 2:
                second_kid = self._get_matching_second_kid(first_parent, area)
                if second_kid is None:
                    second_kid = self._get_random_person_in_age_bracket(
                        area,
                        min_age=self.YOUNG_ADULT_MIN_AGE,
                        max_age=self.YOUNG_ADULT_MAX_AGE,
                    )
                if second_kid is not None:
                    household.people.append(second_kid)

    def fill_nokids_households(
        self,
        adults_per_household: int,
        n_households: int,
        area: Area,
        extra_people_lists=(),
        max_household_size=np.inf,
    ) -> None:
        """
        Fils households with one or two adults.

        Parameters
        ----------
        adults_per_household:
            number of adults to fill in the household can be one or two.
        n_households:
            number of households with this configuration
        area:
            the area in which to put the household
        extra_people_lists:
            whether to include the created households in a list for extra people to be put in.
        max_household_size:
            maximum size of the created households.
        """
        for i in range(0, n_households):
            household = self._create_household(
                area, max_household_size=max_household_size
            )
            # if self._check_if_oldpeople_left(area):
            #    # if there are old people left, then put them here together with another adult.
            #    first_adult = self._get_random_person_in_age_bracket(
            #        area, min_age=self.OLD_MIN_AGE, max_age=self.OLD_MAX_AGE
            #    )
            #    if first_adult is None:
            #        raise HouseholdError("But you said there were old people left!")
            # else:
            #    first_adult = self._get_random_person_in_age_bracket(
            #        area, min_age=self.ADULT_MIN_AGE, max_age=self.ADULT_MAX_AGE
            #    )
            first_adult = self._get_random_person_in_age_bracket(
                area, min_age=self.ADULT_MIN_AGE, max_age=self.ADULT_MAX_AGE
            )
            if first_adult is not None:
                household.people.append(first_adult)
            if adults_per_household == 1:
                if household.size < household.max_size:
                    for array in extra_people_lists:
                        array.append(household)
                continue
            # second_adult = self._get_matching_partner(first_adult, area, under_65=True)
            if first_adult is not None:
                second_adult = self._get_matching_partner(first_adult, area)
            if second_adult is not None:
                household.people.append(second_adult)
            if household.size < household.max_size:
                for array in extra_people_lists:
                    array.append(household)

    def fill_youngadult_households(
        self,
        youngadults_per_household: int,
        n_households: int,
        area: Area,
        extra_people_lists=(),
    ) -> None:
        """
        Fils households with young adults (18 to 35) years old. 

        Parameters
        ----------
        youngadults_per_household:
            number of adults to fill in the household. Can be any positive number.
        n_households:
            number of households with this configuration
        area:
            the area in which to put the household
        extra_people_lists:
            whether to include the created households in a list for extra people to be put in.
        """
        for _ in range(0, n_households):
            household = self._create_household(area)
            for _ in range(youngadults_per_household):
                person = self._get_random_person_in_age_bracket(
                    area,
                    min_age=self.YOUNG_ADULT_MIN_AGE,
                    max_age=self.YOUNG_ADULT_MAX_AGE,
                )
                if person is not None:
                    household.people.append(person)
            for array in extra_people_lists:
                array.append(household)

    def fill_youngadult_with_parents_households(
        self,
        adults_per_household: int,
        n_households: int,
        area: Area,
        extra_people_lists=(),
    ) -> None:
        """
        Fils households with one young adult (18 to 35) and one or two adults. 

        Parameters
        ----------
        youngadults_per_household:
            number of adults to fill in the household. Can be one or two.
        n_households:
            number of households with this configuration
        area:
            the area in which to put the household
        extra_people_lists:
            whether to include the created households in a list for extra people to be put in.
        """
        for _ in range(0, n_households):
            household = self._create_household(area)
            for array in extra_people_lists:
                array.append(household)
            youngadult = self._get_random_person_in_age_bracket(
                area, min_age=self.YOUNG_ADULT_MIN_AGE, max_age=self.YOUNG_ADULT_MAX_AGE
            )
            if youngadult is not None:
                household.people.append(youngadult)
            for _ in range(adults_per_household):
                if youngadult is not None:
                    adult = self._get_random_person_in_age_bracket(
                        area, min_age=youngadult.age + 18, max_age=self.ADULT_MAX_AGE
                    )
                else:
                    adult = self._get_random_person_in_age_bracket(
                        area, min_age=self.ADULT_MIN_AGE, max_age=self.ADULT_MAX_AGE
                    )
                if adult is not None:
                    household.people.append(adult)

    def fill_all_communal_establishments(
        self, n_establishments: int, n_people_in_communal: int, area: Area
    ) -> None:
        """
        Fils all comunnal establishments with the remaining people that have not been allocated somewhere else. 

        Parameters
        ----------
        n_establishments:
            number of communal establishments.
        n_people_in_communal:
            number of people in each communal establishment
        area:
            the area in which to put the household
        """
        ratio = max(int(n_people_in_communal / n_establishments), 1)
        surplus = n_people_in_communal % n_establishments
        people_counter = 0
        while people_counter < n_people_in_communal:
            household = self._create_household(area, communal=True)
            for _ in range(ratio):
                person = self._get_random_person_in_age_bracket(area)
                if person is None:  # this cannot fail, as we have the number.
                    raise HouseholdError("Failed to match communal people.")
                household.people.append(person)
                people_counter += 1
                if people_counter == n_people_in_communal - surplus:
                    for _ in range(surplus):
                        person = self._get_random_person_in_age_bracket(area)
                        household.people.append(person)
                    return None

    def _remove_household_from_all_lists(self, household, lists: list) -> None:
        """
        Removes the given households from all the lists in lists.

        Parameters
        ----------

        household
            an instance of Household.
        lists
            list of lists of households.
        """
        for lis in lists:
            try:
                lis.remove(household)
            except ValueError:
                pass

    def _assert_households_not_max(self, area):
        for household in area.households:
            try:
                assert household.size <= self.MAX_HOUSEHOLD_SIZE
            except:
                for person in household.people:
                    print(person.age)
                raise NotImplementedError

    def _assert_lists_match(self, households_with_space, avail_lists):
        for i, lis in enumerate(avail_lists):
            for household in lis:
                try:
                    assert household in households_with_space
                except:
                    raise ValueError

    def _check_if_household_is_full(self, household: Household):
        """
        Checks if a household is full or has the maximum household size allowed by the Distributor.

        Parameters
        ----------
        household:
            the household to check.
        """
        size = household.size
        condition = (size >= household.max_size) or (size >= self.MAX_HOUSEHOLD_SIZE)
        return condition

    def fill_random_people_to_existing_households(
        self,
        households_with_extra_kids: list,
        households_with_kids: list,
        households_with_extra_youngadults: list,
        households_with_extra_adults: list,
        households_with_extra_oldpeople: list,
        area,
    ) -> None:
        """
        The people that have not been associated a household yet are distributed in the following way. Given the lists in the arguments, we assign each age group according to this preferences:
        Kids -> households_with_extra_kids, households_with_kids, any
        Young adults -> households_with_extra_youngadults, households_with_adults, any
        Adults -> households_with_extra_adults, any
        Old people -> households_with_extra_oldpeople, any.
        
        When we allocate someone to any house, we prioritize the houses that have a small number of people (less than the MAX_HOUSEHOLD_SIZE parameter defined in the __init__)

        Parameters
        ----------
        number_to_fill
            number of remaining people to distribute into spare households.
        households_with_extra_kids
            list of households that take extra kids.
        households_with_kids
            list of households that already have kids. 
        households_with_extra_youngadults
            list of households that take extra young adults.
        households_with_extra_oldpeople
            list of households that take extra old people
        area
            area where households are.
        """
        households_with_space = [
            household
            for household in area.households
            if household.size < household.max_size
        ]
        all_households = households_with_space.copy()
        available_lists = [
            all_households,
            households_with_space,
            households_with_extra_kids,
            households_with_kids,
            households_with_extra_youngadults,
            households_with_extra_adults,
            households_with_extra_oldpeople,
        ]
        available_ages = list(area.men_by_age.keys()) + list(area.women_by_age.keys())
        available_ages = np.sort(np.unique(available_ages))
        people_left_dict = OrderedDict({})
        for age in available_ages:
            people_left_dict[age] = []
            if age in area.men_by_age:
                people_left_dict[age] += area.men_by_age[age]
            if age in area.women_by_age:
                people_left_dict[age] += area.women_by_age[age]
            np.random.shuffle(people_left_dict[age])  # mix men and women

        # fill old people first
        for age in range(self.OLD_MIN_AGE, self.OLD_MAX_AGE + 1):
            if age in people_left_dict:
                for person in people_left_dict[age]:
                    # old with old,
                    # otherwise random
                    household = self._find_household_for_nonkid(
                        [households_with_extra_oldpeople,]
                    )
                    if household is None:
                        household = self._find_household_for_nonkid(
                            [households_with_space, all_households,]
                        )
                    # if household is None:
                    #    household = self._find_household_for_nonkid([area.households])
                    household.people.append(person)
                    if self._check_if_household_is_full(household):
                        self._remove_household_from_all_lists(
                            household, available_lists
                        )

        # now young adults
        for age in range(self.YOUNG_ADULT_MIN_AGE, self.YOUNG_ADULT_MAX_AGE + 1):
            if age in people_left_dict:
                for person in people_left_dict[age]:
                    # print("selecting house for young adults...")
                    household = self._find_household_for_nonkid(
                        [households_with_extra_youngadults,]
                    )
                    if household is None:
                        household = self._find_household_for_nonkid(
                            [households_with_space, all_households,]
                        )
                    # if household is None:
                    #    household = self._find_household_for_nonkid([area.households])
                    household.people.append(person)
                    if self._check_if_household_is_full(household):
                        self._remove_household_from_all_lists(
                            household, available_lists
                        )
        ## now adults
        for age in range(self.YOUNG_ADULT_MAX_AGE + 1, self.ADULT_MAX_AGE + 1):
            if age in people_left_dict:
                for person in people_left_dict[age]:
                    # print("selecting house for adults...")
                    household = self._find_household_for_nonkid(
                        [households_with_extra_adults,]
                    )
                    if household is None:
                        household = self._find_household_for_nonkid(
                            [households_with_space, all_households,]
                        )
                    # if household is None:
                    #    household = self._find_household_for_nonkid([area.households])
                    household.people.append(person)
                    if self._check_if_household_is_full(household):
                        self._remove_household_from_all_lists(
                            household, available_lists
                        )

        ## and lastly, kids
        for age in range(0, self.KID_MAX_AGE + 1):
            if age in people_left_dict:
                for person in people_left_dict[age]:
                    household = self._find_household_for_kid(
                        [households_with_extra_kids,]
                    )
                    if household is None:
                        household = self._find_household_for_nonkid(
                            [
                                households_with_kids,
                                # households_with_space,
                                # all_households,
                            ]
                        )
                    if household is None:
                        household = self._find_household_for_nonkid(
                            [households_with_space, all_households]
                        )
                    household.people.append(person)
                    if self._check_if_household_is_full(household):
                        self._remove_household_from_all_lists(
                            household, available_lists
                        )

    def _find_household_for_kid(self, priority_lists):
        """
        Finds a suitable household for a kid. It first tries to search for a place in priority_lists[0], then 1, etc.

        Parameters
        ----------
        priority_lists:
            list of lists of households. The list should be sorted according to priority allocation.
        """
        for lis in priority_lists:
            list2 = [household for household in lis if household.size > 0]
            if len(list2) == 0:
                continue
            household = np.random.choice(list2)
            return household
        return None

    def _find_household_for_nonkid(self, priority_lists):
        """
        Finds a suitable household for a person over 18 years old (who can live alone). It first tries to search for a place in priority_lists[0], then 1, etc.

        Parameters
        ----------
        priority_lists:
            list of lists of households. The list should be sorted according to priority allocation.
        """
        for lis in priority_lists:
            if len(lis) == 0:
                continue
            household = np.random.choice(lis)
            return household
