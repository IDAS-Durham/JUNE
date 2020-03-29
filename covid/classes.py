"""
This file contains the classes definitions for the code
"""
import numpy as np

class World:
    """
    Stores global information about the simulation
    """
    def __init__(self, input_dict):
        self.people = {}
        self.total_people = 0
        self.decoder_sex = {}
        self.decoder_age = {}
        self.decoder_household_composition = {}
        self.postcodes = self.read_postcodes_census(input_dict)

    def read_postcodes_census(self, input_dict):
        n_residents_df = input_dict.pop("n_residents")
        n_households_df = input_dict.pop("n_households")
        age_df = input_dict.pop("age_freq")
        sex_df = input_dict.pop("sex_freq")
        household_compostion_df = input_dict.pop("household_composition_freq")
        for i, column in enumerate(age_df.columns):
            self.decoder_age[i] = column
        for i, column in enumerate(sex_df.columns):
            self.decoder_sex[i] = column
        for i, column in enumerate(household_compostion_df.columns):
            self.decoder_household_composition[i] = column
        postcodes_dict = {}
        for i, postcode_name in enumerate(n_residents_df.index):
            postcode = Postcode(self,
                                postcode_name,
                                n_residents_df.loc[postcode_name],
                                n_households_df.loc[postcode_name],
                                {
                                    "age_freq": age_df.loc[postcode_name],
                                    "sex_freq" : sex_df.loc[postcode_name],
                                    "household_freq": household_compostion_df.loc[postcode_name]
                                }
                                )
            postcodes_dict[i] = postcode
        return postcodes_dict

class Postcode:
    """
    Stores information about the postcode, like the total population
    number, universities, etc.
    """
    def __init__(self, world, name, n_residents, n_households, census_freq):
        self.world = world
        self.name = name
        self.n_residents = int(n_residents)
        self.n_households = n_households
        self.census_freq = census_freq
        self.check_census_freq_ratios()
        self.people = {}
        self.households = {}

    def check_census_freq_ratios(self):
        for key in self.census_freq.keys():
            try:
                assert np.isclose(np.sum(self.census_freq[key].values), 1.0, atol=0, rtol=1e-5)
            except AssertionError as e:
                raise ValueError(f"Postcode {self.name} key {key}, ratios not adding to 1")



class Household:
    """
    The Household class represents a household and contains information about 
    its residents.
    """

    def __init__(self, house_id, configuration, postcode):
        self.id = house_id
        self.household_composition = configuration
        self.residents = {}
        self.postcode = postcode

class Person:
    """
    Represents a single individual
    """

    def __init__(self, person_id, postcode, age, sex, health_index, econ_index):
        self.id = person_id
        self.age = age
        self.sex = sex
        self.health_index = health_index
        self.econ_index = econ_index
        self.postcode = postcode
        self.household = None

class Adult(Person):

    def __init__(self, postcode, age, sex, health_index, econ_index, employed):
        Person.__init__(self, postcode, age, sex, health_index, econ_index)
        self.employed = employed

class Child(Person):
    def __init__(self, postcode, age, sex, health_index, econ_index):
        Person.__init__(self, postcode, age, sex, health_index, econ_index)






