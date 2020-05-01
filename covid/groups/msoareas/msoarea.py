import numpy as np


class MSOArea:
    """
    Stores information about the MSOA, like the total number of companies, etc.
    """

    def __init__(self, world, name, n_companies):
        """
        The n_companies_* represent the number of companies in a given msoa
        by sector - here we take the nomis definition of sector which gives
        categories such as:
            A: Agriculture, forestry and fishing
            B: Mining and quarrying
            C: Manufacturing
            ...

        This same level of detail is given at the sex-disaggregated level and can
        be used in the Person class in order to distribute jobs to people which
        can be matched up with the businesses at the msoa level.
        """

        self.world = world
        self.name = name
        self.oarea = []
        self.work_people = []
        self.companies = []
        self.hospitals = []


class MSOAreas:
    def __init__(self, world):
        self.world = world
        self.members = []
        self.names_in_order = None
