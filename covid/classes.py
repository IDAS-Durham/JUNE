"""
This file contains the classes definitions for the code
"""

class World:
    """
    Stores global information about the simulation
    """
    def __init__(self, input_dict):
        self.input_dict = input_dict
        self.postcodes_idxtoname, self.postcodes = self.read_postcodes()
        self.people = {}
        self.total_people = 0
        self.total_households = 0

    def read_postcodes(self):
        postcodes_idxtoname = []
        postcodes = {}
        for i, key in enumerate(self.input_dict["postcode_sector"].keys()):
            postcodes_idxtoname.append(key)
            postcodes[i] = Postcode(self,
                                    i,
                                    self.input_dict["postcode_sector"][key]["n_residents"],
                                    self.input_dict["postcode_sector"][key]["census_freq"],
            )
        return postcodes_idxtoname, postcodes

class Postcode:
    """
    Stores information about the postcode, like the total population
    number, universities, etc.
    """

    def __init__(self, world, postcode_id, n_residents, census_freq):
        self.world = world
        self.id = postcode_id 
        self.n_residents = n_residents 
        self.people = {} 
        self.households = {}
        self.census_freq = census_freq


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






