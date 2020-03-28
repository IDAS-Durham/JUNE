PEOPLE_IDS = {}

"""
This file contains the classes definitions for the code
"""

class Household:
    """
    The Household class represents a household and contains information about 
    its residents.
    """

    def __init__(self):
        self.residents = [] # unique ids of residents

class Person:
    """
    Represents a single individual
    """

    def __init__(self, age, sex, health_index, econ_index):
        self.age = age
        self.sex = sex
        self.health_index = health_index
        self.econ_index = econ_index

class Adult(Person):

    def __init__(self, age, sex, health_index, econ_index, employed):
        Person.__init__(self, age, sex, health_index, econ_index)
        self.employed = employed

class Child(Person):
    def __init__(self, age, sex, health_index, econ_index):
        Person.__init__(self, age, sex, health_index, econ_index)

class County:
    """
    Stores information about the county, like the total population
    number, universities, etc.
    """

    def __init__(self, county_id, population_number):
        self.id = county_id
        self.population_number = population
        self.people = [] # ids of residents






