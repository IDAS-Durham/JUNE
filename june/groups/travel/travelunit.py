import numpy as np

class TravelUnit:

    def __init__(self, travelunit_id, city):

        self.travelunit_id = travelunit_id
        self.city = city
        self.passengers = []
        self.max_passengers = 50 # assume all units are of equal size but this could be made more granular later

class TravelUnits:

    def __init__(self):

        self.members = []
