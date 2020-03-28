from random import uniform
from scipy import stats
from classes import World, Person, Postcode, Household

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""

def populate_world(world:World):
    for postcode in world.postcodes:
        populate_postcode(postcode)


def populate_postcode(postcode:Postcode):
    """
    """
    census_freq = postcode.census_freq
    try:
        assert sum(census_freq.values()) == 1
    except:
        raise ValueError("Census frequency values should add to 1")

    random_variable = stats.rv_discrete(values=(census_freq.keys(), census_freq.values()))
    number_of_households = postcode.n_residents // 4 + min(postcode.n_residents % 4, 1)
    for i in range(0,postcode.n_residents):
        household_number = i // 4
        # add 1 to world population
        postcode.world.total_people += 1
        # create person
        person = Person(postcode.world.total_people, postcode, 0, random_variable.rvs(1), 0, 0)
        postcode.people[person.id] = person
        # put person into house
        if i % 4 == 0:
            household = Household(household_number) 
        else:
            household.residents[person.id] = person

