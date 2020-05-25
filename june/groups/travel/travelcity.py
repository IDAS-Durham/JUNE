import numpy as np
import pandas as pd
from scipy import spatial
from june.groups.group import Group, Supergroup

class TravelCity(Group):
    """
    Defines a city with details abouts its metropolitan area and who has arrived at the station after initial distirbution
    """
    
    def __init__(self, city, metro_centroid):
        """
        city: (string) name of the city
        metro_centroid: (array) the centroid of the metropolitan area
        msoas: (list) msoas associated with city
        arrived: (list) people who have arrived at the city
        """
        
        super().__init__()
        
        self.city = city
        self.metro_centroid = metro_centroid
        self.msoas = []
        self.arrived = []

class TravelCities(Supergroup):
    """
    Initialise travel cities based on commute cities
    """

    def __init__(self, commutecities):
        """
        commutecities: (list) members of CommuteCities
        members: (list) list of all travel cities

        Assumptions:
        - Commting is turned on and all commute cities have been distirbuted
        """
        
        self.commutecities = commutecities
        self.members = []

    def init_cities(self):
        'Initialise all cities'

        members = []
        for commutecity in self.commutecities:
            
            travel_city = TravelCity(
                city = commutecity.city,
                metro_centroid = commutecity.metro_centroid,
            )

            members.append(travel_city)

        # fix ordering of cities with London in the correct place for data
        member_order = [0,1,2,3,4,5,10,6,7,8,9]
        for i in member_order:
            self.members.append(members[i])
