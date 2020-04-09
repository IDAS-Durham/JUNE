import numpy as np


class MSOArea:
    """
    Stores information about the MSOA, like the total number of companies, etc.
    """

    def __init__(self, world, name, n_companies):
        self.world = world
        self.name = name
        #self.small_areas = oares
        self.n_companies = n_companies

class MSOAreas:

    def __init__(self, world):
        self.world = world
        self.members = []
