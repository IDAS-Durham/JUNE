import numpy as np


class MSOArea:
    """
    Stores information about the MSOA, like the total number of companies, etc.
    """

    def __init__(self, world, name, oares, companysizes):
        self.world = world
        self.name = name
        self.small_areas = oares
        self.companysizes = companysizes

class MSOAreas:

    def __init__(self):
        self.members = []
