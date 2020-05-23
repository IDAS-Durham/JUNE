import numpy as np
import pandas as pd
from scipy import spatial

class TravelCity(Group):
    """
    Defines a city with details abouts its metropolitan area and who has arrived at the station after initial distirbution
    """
    
    def __init__(self, city, metro_centroid):
        """
        city: (string) name of the city
        metro_centroid: (array) the centroid of the metropolitan area
        msoa: (list)
        people: (Group attribute) people who have arrived at the city
        """
        
        super().__init__()
        
        self.city = city
        self.metro_centroid = metro_centroid
        self.msoa = []

class TravelCities(SuperGroup):
    """
    Initialise travel cities based on commute cities
    """

    def __init__(self, commutecities):
        """
        commutecities: (list) members of CommuteCities
        members: (list) list of all travel cities
        """
        
        self.commutecities = commutecities
        self.members = []

    def init_cities(self):

        for commutecity in self.commutecities:

            travel_city = TravelCity(
                id = commutecity.id,
                city = commutecity.city,
                metro_centroid = commutecity.metrocentroid,
            )

            self.members.append(travel_city)
