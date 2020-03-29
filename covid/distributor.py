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


def populate_postcode(postcode:Postcode):
    """
    Populates a postcode with houses and people according to the census frequencies
    """
    age_freq = postcode.census_freq["age_freq"]
    sex_freq = postcode.census_freq["sex_freq"]
    n_residents = postcode.n_residents
    n_households = postcode.n_households
    # create a random variable with the census data to sample from it
    sex_random_variable = stats.rv_discrete(values=(np.arange(0,len(sex_freq)),
                                                    sex_freq.values))
    age_random_variable = stats.rv_discrete(values=(np.arange(0,len(age_freq)),
                                                    age_freq.values))
    sex_sampling = sex_random_variable.rvs(size = postcode.n_residents)
    age_sampling = age_random_variable.rvs(size = postcode.n_residents)
    people_ids = np.arange(postcode.world.total_people + 1, postcode.world.total_people + postcode.n_residents + 1)
    # create people and record it to the world and postcodes
    for i in range(0, postcode.n_residents):
        if i % 4 == 0:
            household = Household(i//4, postcode)
        person = Person(people_ids[i], postcode, age_sampling[i], sex_sampling[i], 0, 0) 
        household.residents[i%4] = person
        postcode.households[i%4] = household
        postcode.world.total_people += 1
        postcode.world.people[postcode.world.total_people] = person
        postcode.people[postcode.world.total_people] = person
