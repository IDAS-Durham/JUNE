import numpy as np


class MSOArea:
    """
    Stores information about the MSOA, like the total number of companies, etc.
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

    def __init__(self, world, coordinates, pcd: list, oa: list, name: str):
        """
        """
        self.world = world
        self.coordinates = coordinates  # Lon. & Lat
        self.pcd = pcd                  # Postcode
        self.oarea = oa                 # Output Area
        self.name = name                # Middle Super Output Area
        # collect people
        self.work_people = []
        for relevant_groups in world.relevant_groups:
            setattr(self, relevant_groups, [])


class MSOAreas:
    def __init__(self, world):
        self.world = world
        self.members = []
        self.names_in_order = None  # for fast search
