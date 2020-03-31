import numpy as np
from random import uniform
from scipy import stats
import warnings
from covid.classes import World,  Area, Household
from covid.person import Person

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""

class Distributor:
    def __init__(self, area):
        self.ADULT_THRESHOLD = 6 # 6 corresponds to 18-19 years old
        self.area = area
        self._init_random_variables()
        self.residents_available = area.n_residents
        self.people_counter = 0
        self.no_kids_area = False

    def _init_random_variables(self):
        age_freq = self.area.census_freq["age_freq"]
        sex_freq = self.area.census_freq["sex_freq"]
        household_freq = self.area.census_freq["household_freq"]
        n_households = self.area.n_households
        # create a random variable with the census data to sample from it
        self.sex_rv = stats.rv_discrete(values=(np.arange(0,len(sex_freq)),sex_freq.values))
        # create random variables for adult and kids age
        age_kids_freq = age_freq.values[:self.ADULT_THRESHOLD]
        if np.sum(age_kids_freq) == 0:
            self.no_kids_area = True
        else:
            age_kid_freqs_norm =  age_kids_freq / np.sum(age_kids_freq)
            self.kid_age_rv = stats.rv_discrete(values=(np.arange(0, self.ADULT_THRESHOLD), age_kid_freqs_norm))
        adult_freqs_norm = age_freq.values[self.ADULT_THRESHOLD:] / np.sum(age_freq.values[self.ADULT_THRESHOLD:])
        self.adult_age_rv = stats.rv_discrete(values=(np.arange(self.ADULT_THRESHOLD, len(age_freq)), adult_freqs_norm))
        self.age_rv = stats.rv_discrete(values=(np.arange(0, len(age_freq)), age_freq.values))
        # random variable for household freq.
        self.household_rv = stats.rv_discrete(values=(np.arange(0,len(household_freq)), household_freq.values))
        self.age_groups_rv = stats.rv_discrete(values=([-1, 0, 1], [0.2, 0.6, 0.2]))
        self.same_sex_rv = stats.rv_discrete(values=([0,1], [0.9, 0.1])) # when we match sex, we assume 10% of first 2 adults have same sex.

    def _compute_compatible_adult_age(self, first_adult_age):
        age_variation = self.age_groups_rv.rvs(size=1)[0]
        if first_adult_age == len(self.area.world.decoder_age) - 1:
            age = first_adult_age - abs(age_variation)
        elif first_adult_age == self.ADULT_THRESHOLD:
            age = first_adult_age + abs(age_variation)
        else:
            age = first_adult_age + age_variation
        return age

    def _init_person_to_household(self, age, sex, household, household_person_number):
        person = Person(self.area.world.total_people,
                        self.area,
                        age,
                        sex,
                        0,
                        0)
        person.household = household
        household.residents[household_person_number] = person
        self.area.people[self.people_counter] = person
        self.area.world.people[self.area.world.total_people] = person
        self.area.world.total_people += 1
        self.people_counter += 1
        self.residents_available -= 1
        if self.residents_available <= 0:
            return False
        else:
            return True

    def populate_household(self, household):
        household_composition_decoded = self.area.world.decoder_household_composition[household.household_composition]
        n_kids, n_adults, n_old, n_other = household_composition_decoded.split(" ")
        n_adults = int(n_adults) + int(n_old) + int(n_other) # ! assume for now this
        n_kids = int(n_kids)
        if self.no_kids_area:
            n_kids = 0
        # first populate with an adult with random age and sex
        self.area.world.total_people += 1
        age = self.adult_age_rv.rvs(size=1)[0]
        sex = self.sex_rv.rvs(size=1)[0]
        first_adult_sex = sex
        first_adult_age = age
        people_left = self._init_person_to_household(age, sex, household, 0)
        if not people_left:
            return household
        if n_adults == 1:
            if n_kids == 0:
                return household
            else:
                # fill with random kids
                for i in range(0, n_kids):
                    age = self.kid_age_rv.rvs(size=1)[0]
                    sex = self.sex_rv.rvs(size=1)[0]
                    people_left = self._init_person_to_household(age, sex, household, i+1)
                    if not people_left:
                        return household
                return household
        else:
            # fill another adult with matching sex 
            same_sex = self.same_sex_rv.rvs(size=1)[0]
            if same_sex == 0:
                matching_sex = int(not first_adult_sex)
            else:
                matching_sex = first_adult_sex
            matching_age = self._compute_compatible_adult_age(first_adult_age) 
            people_left = self._init_person_to_household(matching_age, matching_sex, household, 1)
            if not people_left:
                return household
            if n_kids == 0:
                if n_adults == 2:
                    return household
                else:
                    # fill with random adults
                    for i in range(0, n_adults-2):
                        sex = self.sex_rv.rvs(size=1)[0]
                        matching_age = self._compute_compatible_adult_age(first_adult_age) 
                        people_left = self._init_person_to_household(matching_age, sex, household, i+2)
                        if not people_left:
                            return household
                    return household
            else:
                # fill with random kids
                for i in range(0, n_kids):
                    sex = self.sex_rv.rvs(size=1)[0]
                    age = self.kid_age_rv.rvs(size=1)[0]
                    people_left = self._init_person_to_household(age, sex, household, i+2)
                    if not people_left:
                        return household
                return household

    def populate_area(self):
        people_counter = 0
        for house_id in range(0, self.area.n_households):
            composition_id = self.household_rv.rvs(size=1)[0]
            household = Household(house_id, composition_id, self.area)
            self.area.households[house_id] = household
            self.populate_household(household)
            household.n_residents = len(household.residents)
            if self.residents_available <= 0:
                break
        # check if there are still people left to allocate, if so,
        # allocate them randomly in the previous houses
        while self.residents_available > 0:
            random_hs_idx = np.random.randint(0, len(self.area.households))
            random_household = self.area.households[random_hs_idx]
            random_sex = self.sex_rv.rvs(size=1)[0]
            random_age = self.age_rv.rvs(size=1)[0]
            self._init_person_to_household(random_age, random_sex, random_household, len(household.residents)+1)

def populate_world(world:World):
    """
    Populates all areas in the world.
    """
    print("Populating areas...")
    for area in world.areas.values():
        distributor = Distributor(area)
        distributor.populate_area()
        print("#", end="")
        #populate_area(area)
    print("\n")

