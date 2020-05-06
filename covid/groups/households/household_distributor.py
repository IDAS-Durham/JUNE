import numpy as np
from scipy import stats

from covid.groups.households import Household

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""


class HouseholdError(BaseException):
    """ class for throwing household related errors """

    pass


class HouseholdDistributor:
    """
    Contains routies to populate the given area with a realistic population with attributes based
    on census data from NOMIS. 
    Note: in this class student refers to an adult age 18-25, independently of they being a student or not.
    """

    def __init__(self, households, area, areas, config: dict):
        self.households = households
        self.area = area
        self.areas = areas
        self.SAME_SEX_COUPLE_RATIO = config["households"]["same_sex_couple_ratio"]
        self.area = area
        self._init_random_variables()

    def _init_random_variables(self):
        """
        Reads the frequencies for different attributes based on the census data,
        and initializes random variables following the discrete distributions.
        """
        household_freq = self.area.census_freq["household_freq"]
        n_households = self.area.n_households
        # random variable for household freq.
        self.household_rv = stats.rv_discrete(
            values=(np.arange(0, len(household_freq)), household_freq.values)
        )
        # random variable for the probability of a couple having different age groups,
        # -1 lower group, 0 same, +1 upper, currently this is not used.
        # self.age_groups_rv = stats.rv_discrete(values=([-1, 0, 1], [0.2, 0.6, 0.2]))
        # when we match sex in a couple, we assume 10% of first 2 adults have same sex.
        self.same_sex_rv = stats.rv_discrete(
            values=(
                [0, 1],
                [1 - self.SAME_SEX_COUPLE_RATIO, self.SAME_SEX_COUPLE_RATIO],
            )
        )

    def _fill_random_man(self, household):
        """
        Fils a random man to a household, if it is a student,
        it also deletes it from the student list.
        """
        man = self.area._men.popitem()
        household.add(man[1], Household.GroupType.adults)
        try:
            del self.area._student_keys[man[0]]
        except KeyError:
            pass

    def _fill_random_woman(self, household):
        """
        Fils a random woman to a household, if it is a student,
        it also deletes it from the student list.
        """
        woman = self.area._women.popitem()
        household.add(woman[1], Household.GroupType.adults)
        try:
            del self.area._student_keys[woman[0]]
        except KeyError:
            pass

    def _compute_compatible_adult_age(self, first_adult_age):
        """
        Given an adult age, returns an age in the same group with a certain probability,
        and in one upper or lower group with another probability. (Default is 60/40)
        """
        age_variation = self.age_groups_rv.rvs(size=1)[0]
        if first_adult_age == len(self.areas.decoder_age) - 1:
            age = first_adult_age - abs(age_variation)
        elif first_adult_age == self.ADULT_THRESHOLD:
            age = first_adult_age + abs(age_variation)
        else:
            age = first_adult_age + age_variation
        return age

    def _create_student_household(self, n_students, household):
        """
        Creates a student flat, filled randomly with men and women
        between 18-24 age both inclusive.
        Returns -1 if the house is empty, and the number of filled
        students otherwise.
        """
        if not self.area._student_keys:
            return -1  # empty house
        for i in range(0, n_students):
            if not self.area._student_keys:
                return i
            student_key = self.area._student_keys.popitem()[0]
            try:  # check if man
                student = self.area._men.pop(student_key)
            except KeyError:
                student = self.area._women.pop(student_key)
            household.add(student, Household.GroupType.young_adults)
        return n_students

    def _create_oldpeople_household(self, n_old, household):
        """
        Creates a household with old people( 65+ ) living in it.
        We currently assume old people live alone or in couples.
        Returns -1 if the house is left empty, and the number
        of old people otherwise.
        """
        if not self.area._oldmen:  # no men left, just fill with women
            if not self.area._oldwomen:
                return -1
            else:
                household.add(self.area._oldwomen.popitem()[1], Household.GroupType.old_adults)
                if n_old >= 2 and self.area._oldwomen:
                    household.add(self.area._oldwomen.popitem()[1], Household.GroupType.old_adults)
                    if n_old == 3 and self.area._oldwomen:
                        household.add(self.area._oldwomen.popitem()[1], Household.GroupType.old_adults)
                        return 3
                    else:
                        return 2
                else:
                    return 1
        elif not self.area._oldwomen:  # no women left, fill with men
            household.add(self.area._oldmen.popitem()[1], Household.GroupType.old_adults)
            if n_old >= 2 and self.area._oldmen:
                household.add(self.area._oldmen.popitem()[1], Household.GroupType.old_adults)
                if n_old == 3 and self.area._oldmen:
                    household.add(self.area._oldmen.popitem()[1], Household.GroupType.old_adults)
                    return 3
                else:
                    return 2
            else:
                return 1
        # here we have at least one man and at least one woman
        # n = 3 case
        if n_old == 3:  # if its three people, just fill random sex
            for i in range(0, 3):
                old_sex = self.area.sex_rv.rvs(size=1)[0]
                if old_sex == 0 or not self.area._oldwomen:
                    if not self.area._oldmen:
                        if i == 0:
                            return -1
                        else:
                            return i
                    else:
                        household.add(self.area._oldmen.popitem()[1], Household.GroupType.old_adults)
                elif old_sex == 1 or not self.area._oldmen:
                    household.add(self.area._oldwomen.popitem()[1], Household.GroupType.old_adults)
            return 3
        # n <= 2 case
        old_sex = self.area.sex_rv.rvs(size=1)[0]
        if old_sex == 0:  # it is a man
            household.add(self.area._oldmen.popitem()[1], Household.GroupType.old_adults)
            if n_old == 1:
                return 1
            else:
                if self.area._oldwomen:
                    household.add(self.area._oldwomen.popitem()[1], Household.GroupType.old_adults)
                    return 2
                elif self.area._oldmen:
                    household.add(self.area._oldmen.popitem()[1], Household.GroupType.old_adults)
                    return 2
                else:
                    return 1
        else:
            household.add(self.area._oldwomen.popitem()[1], Household.GroupType.old_adults)
            if n_old == 1:
                return 1
            else:
                if self.area._oldmen:
                    household.add(self.area._oldmen.popitem()[1], Household.GroupType.old_adults)
                    return 2
                elif self.area._oldwomen:
                    household.add(self.area._oldwomen.popitem()[1], Household.GroupType.old_adults)
                    return 2
                else:
                    return 1

    def _create_singleparent_household(self, n_kids, n_students, household):
        """
        Creates single parent household. The sex of the parent
        is randomized. 
        Returns (-1,-1) if the house is left empty,
        otherwise (n,m) where n is the number of filled kids, and m
        the number of filled students.
        """
        # add adult
        adult_sex = self.area.sex_rv.rvs(size=1)[0]
        if (
                adult_sex == 0 or not self.area._women
        ):  # if the sex is man or there are no women left
            if not self.area._men:  # no men left
                return -1, -1
            else:
                self._fill_random_man(household)
        elif adult_sex == 1 or not self._man:
            self._fill_random_woman(household)

        # add dependable kids
        filled_kids = 0
        if not self.area._kids:  # no kids left
            pass
        else:
            for i in range(0, min(n_kids, len(self.area._kids.keys()))):
                household.add(self.area._kids.popitem()[1], Household.GroupType.kids)
                filled_kids += 1
        # add non dependable kids
        filled_students = 0
        if n_students == 0:
            return filled_kids, 0  # kids filled, students filled
        else:
            for i in range(0, min(n_students, len(self.area._student_keys))):
                student_key = self.area._student_keys.popitem()[0]
                try:
                    student = self.area._men.pop(student_key)
                except KeyError:
                    student = self.area._women.pop(student_key)
                household.add(student, Household.GroupType.young_adults)
                filled_students += 1
        return filled_kids, filled_students

    def _create_twoparent_household(self, n_kids, n_students, household):
        """
        Creates two parent household. Parents are assumed to have
        the same sex, however homosexual couples are created when
        that is not possible.
        Returns (-1,-1,-1) if the house is left empty,
        otherwise (n,m,l) where n is the number of filled kids, m
        the number of filled students, and l is the number of filled 
        adults.
        """
        # first adult
        if self.area._men:
            self._fill_random_man(household)
        else:
            if not self.area._women:
                return -1, -1, -1
            else:
                self._fill_random_woman(household)
        filled_adults = 1
        # second adult
        if self.area._women:
            self._fill_random_woman(household)
            filled_adults += 1
        else:
            if not self.area._men:
                pass
            else:
                self._fill_random_man(household)
                filled_adults += 1
        # add kids
        filled_kids = 0
        if not self.area._kids:  # no kids left
            pass
        else:
            for i in range(0, min(n_kids, len(self.area._kids.keys()))):
                household.add(self.area._kids.popitem()[1], Household.GroupType.kids)
                filled_kids += 1
        # add non dependable kids
        filled_students = 0
        if n_students == 0:
            pass
        else:
            for i in range(0, min(n_students, len(self.area._student_keys))):
                student_key = self.area._student_keys.popitem()[0]
                try:
                    student = self.area._men.pop(student_key)
                except KeyError:
                    student = self.area._women.pop(student_key)
                household.add(student, Household.GroupType.young_adults)
                filled_students += 1
        return filled_kids, filled_students, filled_adults

    def populate_household(self, household):
        """
        Given a household with a certain household composition, fills it from the available 
        people pool.
        """
        household_composition_decoded = self.areas.decoder_household_composition[
            household.household_composition
        ]
        n_kids, n_students, n_adults, n_old = map(
            int, household_composition_decoded.split(" ")
        )
        if n_adults == 0:  # then its either student flat or old people house
            if n_kids != 0:
                raise HouseholdError("There are kids in a student/old house")
            if n_students != 0 and n_old == 0:
                n_students = self._create_student_household(n_students, household)
                if n_students == -1:
                    return -1
                return f"0 {n_students} 0 0"
            elif n_students == 0 and n_old != 0:
                n_old = self._create_oldpeople_household(n_old, household)
                if n_old == -1:
                    return -1
                return f"0 0 0 {n_old}"
            else:
                raise HouseholdError("Household composition not possible!")
        elif (
                n_adults == 1
        ):  # adult living alone or monoparental family with n_kids and n_students (independent child)
            n_kids, n_students = self._create_singleparent_household(
                n_kids, n_students, household
            )
            if n_kids == -1:
                return -1
            return f"{n_kids} {n_students} 1 0"
        elif (
                n_adults == 2
        ):  # two parents family with n_kids and n_students (independent child)
            n_kids, n_students, n_adults = self._create_twoparent_household(
                n_kids, n_students, household
            )
            if n_kids == -1:
                return -1
            return f"{n_kids} {n_students} {n_adults} 0"
        else:
            raise HouseholdError("error number of adults have to be 0,1 or 2")

    def distribute_people_to_household(self):
        #if len(self.area.people) == 0:
        #    self.populate_area()
        house_id = 0
        aux = False
        composition_id_array = self.household_rv.rvs(size=self.area.n_residents)
        i = 0
        maxi = len(composition_id_array)
        while self.area._men or self.area._women or self.area._oldmen or self.area._oldwomen:
            if not self.area._men and not self.area._women:  #
                """
                Only old people left.. just fill them in pairs this is to avoid
                problems in areas where old people live but no household composition 
                exists for them
                """
                composition_id = self.areas.encoder_household_composition["0 0 0 2"]
                household = Household(house_id, composition_id, self.area)
                household_filled_config = self.populate_household(household)
            else:
                # composition_id = self.household_rv.rvs(size=1)[0]
                composition_id = composition_id_array[i]
                i += 1
                if i >= maxi:
                    composition_id_array = self.household_rv.rvs(size=self.area.n_residents)
                    i = 0

                household = Household(house_id, composition_id, self.area)
                household_filled_config = self.populate_household(household)
            if household_filled_config == -1:  # empty house
                continue
            else:
                # store actual household config
                try: # the key might not exist yet
                    household.household_composition = self.areas.encoder_household_composition[
                        household_filled_config
                    ]
                except KeyError:
                    aux = True
                    lastkey = len(self.areas.decoder_household_composition)
                    self.areas.decoder_household_composition[lastkey] = household_filled_config
                    self.areas.encoder_household_composition[household_filled_config] = lastkey 
                    household.household_composition = self.areas.encoder_household_composition[
                        household_filled_config
                    ]
            self.households.members.append(household)
            self.area.households.append(household)
            house_id += 1
        self.kids_left = len(self.area._kids)
        if self.kids_left > 0:
            random_houses = np.random.choice(self.area.households, size=self.kids_left)
            for i, kid in enumerate(self.area._kids.values()):
                random_houses[i].add(kid, Household.GroupType.kids)
