import numpy as np
from random import uniform
from scipy import stats
import warnings
from covid.classes import World, Person, Area, Household

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""

def populate_world(world:World):
    """
    Populates all areas in the world.
    """
    print("Populating areas...")
    for area in world.areas.values():
        print("#", end="")
        populate_area(area)
    print("\n")

def populate_household(household, configuration, adults, kids, old):
    counter = 0
    n_kids, n_adults, n_old, n_oldadult = configuration.split(" ")
    n_kids = int(n_kids)
    n_adults = int(n_adults)
    n_old = int(n_old)
    n_oldadult = int(n_oldadult)
    n_adults = n_adults + n_oldadult
    if n_kids > len(kids):
        warnings.warn("Warning, too few kids to fill household")
        n_kids = len(kids)
    if n_old > len(old):
        warnings.warn("Warning, too few old people to fill household")
        n_old = len(old)
    if n_adults > len(adults):
        warnings.warn("Warning, too few adults to fill household")
        n_adults = len(adults)
    for i in range(0, n_kids):
        kid = kids.pop()
        kid.household = household
        household.residents[counter] = kid
        counter += 1
    for i in range(0, n_adults):
        adult = adults.pop()
        adult.household = household
        household.residents[counter] = adult 
        counter += 1
    for i in range(0, n_old):
        oldperson = old.pop()
        oldperson.household = household
        household.residents[counter] = oldperson
        counter += 1

def populate_area(area:Area):
    """
    Populates a area with houses and people according to the census frequencies
    """
    ADULT_THRESHOLD = 6 # 6 corresponds to 18-19 years old
    OLD_THRESHOLD = 12 # 12 corresponds to 65-74 years old
    age_freq = area.census_freq["age_freq"]
    sex_freq = area.census_freq["sex_freq"]
    household_freq = area.census_freq["household_freq"]
    n_residents = area.n_residents
    n_households = area.n_households
    # create a random variable with the census data to sample from it
    sex_random_variable = stats.rv_discrete(values=(np.arange(0,len(sex_freq)),
                                                    sex_freq.values))
    age_random_variable = stats.rv_discrete(values=(np.arange(0,len(age_freq)),
                                                    age_freq.values))
    household_random_variable = stats.rv_discrete(values=(np.arange(0,len(household_freq)),
                                                    household_freq.values))

    # sample from random variables
    sex_sampling = sex_random_variable.rvs(size = area.n_residents)
    age_sampling = age_random_variable.rvs(size = area.n_residents)
    household_sampling = household_random_variable.rvs(size = area.n_residents)
    people_ids = np.arange(area.world.total_people+1,
                           area.world.total_people+area.n_residents+1)
    # create area population
    adults = []
    kids = []
    old = []
    for i in range(0, area.n_residents):
        area.world.total_people += 1
        person = Person(people_ids[i], area, age_sampling[i], sex_sampling[i], 0, 0) 
        if person.age < ADULT_THRESHOLD:
            kids.append(person)
        else:
            if person.age >= OLD_THRESHOLD:
                old.append(person)
            else:
                adults.append(person)
        area.people[i] = person
        area.world.people[area.world.total_people] = person

    # create houses for the world population 
    house_id = 0
    while (len(adults) > 0 or len(kids) > 0 or len(old) > 0) and (house_id < n_households):
        configuration = household_sampling[house_id]
        household = Household(house_id, configuration, area)
        house_id += 1
        configuration_decoded = area.world.decoder_household_composition[configuration]
        populate_household(household, configuration_decoded, adults, kids, old)
        area.households[house_id] = household

