import numpy as np
from june.groups.group import Group, Supergroup

class TravelUnit(Group):

    def __init__(self, city):
        """
        city: (string) City unit belongs to
        people: (Group structure) passengers travelingin the travel unit
        no_passengers: (int) number of passengers in travel unit
        max_passengers: (int) capacity of the travel unit
        """
        super().__init__()
        
        self.city = city
        self.passengers = []
        self.no_passengers = 0
        self.max_passengers = 50 # assume all units are of equal size but this could be made more granular later

class TravelUnits(Supergroup):
    """
    Initialise travel unit members list to be dynamically filled as people fill units
    """

    def __init__(self):

        super().__init__([])

