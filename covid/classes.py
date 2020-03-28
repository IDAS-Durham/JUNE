"""
This file contains the classes definitions for the code
"""

class World:
    """
    Stores global information about the simulation
    """
    def __init__(self, input_df):
        self.input_df = input_df
        self.postcodes = self.read_postcodes_census()
        self.people = {}
        self.total_people = 0

    def read_postcodes_census(self):
        postcodes_dict = {}
        postcodes = self.input_df.apply(lambda row: Postcode(self, row.name, row["n_residents"], row["n_households"], row[["males", "females"]]), axis=1)
        for i, postcode in enumerate(postcodes):
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
        self.people = {}
        self.households = {}


class Household:
    """
    The Household class represents a household and contains information about 
    its residents.
    """

    def __init__(self, house_id, postcode):
        self.id = house_id
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

class Adult(Person):

    def __init__(self, postcode, age, sex, health_index, econ_index, employed):
        Person.__init__(self, postcode, age, sex, health_index, econ_index)
        self.employed = employed

class Child(Person):
    def __init__(self, postcode, age, sex, health_index, econ_index):
        Person.__init__(self, postcode, age, sex, health_index, econ_index)






