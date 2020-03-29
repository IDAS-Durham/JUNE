import numpy as np
from random import uniform
from scipy import stats
from covid.classes import World, Person, Postcode, Household

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""

def populate_world(world:World):
    """
    Populates all postcodes in the world.
    """
    print("Populating postcodes...")
    for postcode in world.postcodes.values():
        print("#", end="")
        populate_postcode(postcode)
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
        print("Warning, too few kids to fill household")
        n_kids = len(kids)
    if n_old > len(old):
        print("Warning, too few old people to fill household")
        n_old = len(old)
    if n_adults > len(adults):
        print("Warning, too few adults to fill household")
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

def populate_postcode(postcode:Postcode):
    """
    Populates a postcode with houses and people according to the census frequencies
    """
    ADULT_THRESHOLD = 6 # 6 corresponds to 18-19 years old
    OLD_THRESHOLD = 12 # 12 corresponds to 65-74 years old
    age_freq = postcode.census_freq["age_freq"]
    sex_freq = postcode.census_freq["sex_freq"]
    household_freq = postcode.census_freq["household_freq"]
    n_residents = postcode.n_residents
    n_households = postcode.n_households
    # create a random variable with the census data to sample from it
    sex_random_variable = stats.rv_discrete(values=(np.arange(0,len(sex_freq)),
                                                    sex_freq.values))
    age_random_variable = stats.rv_discrete(values=(np.arange(0,len(age_freq)),
                                                    age_freq.values))
    household_random_variable = stats.rv_discrete(values=(np.arange(0,len(household_freq)),
                                                    household_freq.values))

    # sample from random variables
    sex_sampling = sex_random_variable.rvs(size = postcode.n_residents)
    age_sampling = age_random_variable.rvs(size = postcode.n_residents)
    household_sampling = household_random_variable.rvs(size = postcode.n_residents)
    people_ids = np.arange(postcode.world.total_people+1,
                           postcode.world.total_people+postcode.n_residents+1)
    # create postcode population
    adults = []
    kids = []
    old = []
    for i in range(0, postcode.n_residents):
        postcode.world.total_people += 1
        person = Person(people_ids[i], postcode, age_sampling[i], sex_sampling[i], 0, 0) 
        if person.age < ADULT_THRESHOLD:
            kids.append(person)
        else:
            if person.age >= OLD_THRESHOLD:
                old.append(person)
            else:
                adults.append(person)
        postcode.world.people[postcode.world.total_people] = person

    # create houses for the world population 
    house_id = 0
    while (len(adults) > 0 or len(kids) > 0 or len(old) > 0) and (house_id < n_households):
        configuration = household_sampling[house_id]
        household = Household(house_id, configuration, postcode)
        house_id += 1
        configuration_decoded = postcode.world.decoder_household[configuration]
        populate_household(household, configuration_decoded, adults, kids, old)
        postcode.households[house_id] = household

