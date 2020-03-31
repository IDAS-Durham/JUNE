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
        self.init_random_variables()

    def init_random_variables(self):
        age_freq = self.area.census_freq["age_freq"]
        sex_freq = self.area.census_freq["sex_freq"]
        household_freq = self.area.census_freq["household_freq"]
        n_residents = self.area.n_residents
        n_households = self.area.n_households
        # create a random variable with the census data to sample from it
        self.sex_random_variable = stats.rv_discrete(values=(np.arange(0,len(sex_freq)),sex_freq.values))
        # create random variables for adult and kids age
        age_kid_freqs_norm = age_freq.values[:self.ADULT_THRESHOLD] / np.sum(age_freq.values[:self.ADULT_THRESHOLD])
        adult_freqs_norm = age_freq.values[self.ADULT_THRESHOLD:] / np.sum(age_freq.values[self.ADULT_THRESHOLD:])
        self.kid_age_rv = stats.rv_discrete(values=(np.arange(0, self.ADULT_THRESHOLD), age_kid_freqs_norm))
        self.adult_age_rv = stats.rv_discrete(values=(np.arange(self.ADULT_THRESHOLD, len(age_freq)), adult_freqs_norm))
        # random variable for household freq.
        self.household_rv = stats.rv_discrete(values=(np.arange(0,len(household_freq)), household_freq.values))

    def populate_household(self, household):
        n_kids, n_adults, n_old, n_other = household.household_composition.split(" ")
        n_adults = int(n_adults) + int(n_old) + int(n_other) # ! assume for now this
        n_kids = int(n_kids)
        # first populate with an adult with random age and sex
        self.area.world.total_people += 1
        person = Person(self.area.world.total_people,
                        self.area,
                        self.adult_age_rv.rvs(size=1),
                        self.sex_random_variable(1),
                        0,
                        0)
        first_adult_sex = person.sex
        person.household = household
        household.residents[0] = person
        self.area.world.people[self.area.world.total_people] = person
        if n_adults == 1:
            if n_kids == 0:
                return household
            else:
                # fill with random kids
                for i in range(0, n_kids):
                    self.area.world.total_people += 1
                    person = Person(self.area.world.total_people,
                                    self.area,
                                    self.kid_age_rv.rvs(size=1),
                                    self.sex_random_variable(1),
                                    0,
                                    0)
                    person.household = household
                    household.residents[i+1] = person
                    self.area.world.people[self.area.world.total_people] = person
                return household
        else:
            # fill another adult with matching sex 
            matching_sex = int(not first_adult_sex)
            self.area.world.total_people += 1
            person = Person(self.area.world.total_people,
                            self.area,
                            self.adult_age_rv.rvs(size=1),
                            matching_sex,
                            0,
                            0)
            person.household = household
            household.residents[1] = person
            self.area.world.people[self.area.world.total_people] = person
            if n_kids == 0:
                if n_adults == 2:
                    return household
                else:
                    # fill with random adults
                    for i in range(0, n_adults-2):
                        self.area.world.total_people += 1
                        person = Person(self.area.world.total_people,
                                        self.area,
                                        self.adult_age_rv.rvs(size=1),
                                        self.sex_random_variable(1),
                                        0,
                                        0)
                        person.household = household
                        household.residents[i+2] = person
                        self.area.world.people[self.area.world.total_people] = person
                    return household

            else:
                # fill with random kids
                for i in range(0, n_kids):
                    self.area.world.total_people += 1
                    person = Person(self.area.world.total_people,
                                    self.area,
                                    self.kid_age_rv.rvs(size=1),
                                    self.sex_random_variable(1),
                                    0,
                                    0)
                    person.household = household
                    household.residents[i+2] = person
                    self.area.world.people[self.area.world.total_people] = person
                return household

    def populate_area(self):
        total_residents = 0
        for house_id in range(0, self.area.n_households):
            composition_id = self.household_rv.rvs(size=1)[0]
            composition = self.area.world.decoder_household_composition[composition_id]
            household = Household(house_id, composition, self.area)
            self.area.households[house_id] = household
            self.populate_household(household)
            household.n_residents = len(household.residents)
            total_residents += household.n_residents
        self.area.n_residents = total_residents



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

