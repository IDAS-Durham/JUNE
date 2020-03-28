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


def populate_postcode(postcode:Postcode):
    """
    Populates a postcode with houses and people according to the census frequencies
    """
    census_freq = postcode.census_freq
    n_residents = postcode.n_residents
    try:
        assert np.sum(census_freq.values) == 1
    except:
        raise ValueError("Census frequency values should add to 1")

    # create a random variable with the census data to sample from it
    random_variable = stats.rv_discrete(values=(np.arange(0,len(census_freq)), census_freq.values))
    residents_sex_random = random_variable.rvs(size = postcode.n_residents)
    people_ids = np.arange(postcode.world.total_people + 1, postcode.world.total_people + postcode.n_residents + 1)
    # create people and record it to the world and postcodes
    for i in range(0, postcode.n_residents):
        person = Person(people_ids[i], postcode, 0, residents_sex_random[i], 0, 0) 
        postcode.world.total_people += 1
        postcode.world.people[postcode.world.total_people] = person
        postcode.people[postcode.world.total_people] = person
