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
    try:
        assert sum(census_freq.values()) == 1
    except:
        raise ValueError("Census frequency values should add to 1")

    # create a random variable with the census data to sample from it
    census_keys_values_array = (np.array(list(census_freq.keys())), np.array(list(census_freq.values())))
    random_variable = stats.rv_discrete(values=census_keys_values_array)
    number_of_households = postcode.n_residents // 4 + min(postcode.n_residents % 4, 1)
    for i in range(0,postcode.n_residents):
        household_number = postcode.world.total_households + i // 4
        # add 1 to world population
        postcode.world.total_people += 1
        # create person
        person = Person(postcode.world.total_people, postcode, 0, random_variable.rvs(1), 0, 0)
        postcode.people[person.id] = person
        # put person into house
        if i % 4 == 0:
            household = Household(household_number, postcode) 
            postcode.households[household_number] = household
        else:
            household.residents[person.id] = person

