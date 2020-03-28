from random import uniform
"""
This file contains routines to attribute people with different characteristics
according to census data.
"""

def assign_people_to_household(household, ratios_data):
    """
    Assigns a certain resident configuration to a household.
    The input is a dictionary with each configuration and the probability.
    The first number of the key is the number of adults, and the second one is the number
    of kids.
    example = {
        "2 0" : 0.1,
        "2 1" : 0.6,
        "1 1" : 0.3,
    }
    """
    try:
        assert sum(ratios_data.values()) == 1
    except:
        raise ValueError("ratios should add to 1")
    configurations = []
    pdf_values = []
    total = 0
    random_number = uniform(0, 1)
    for key in ratios_data.keys():
        config_probability = ratios_data[key]
        total += config_probability
        if total >= random_number:
            return key
    raise ValueError("whoops, should not be here!")

def populate_county(county, ratios_data): 
    total_pop = county.population_number


    



