import numpy as np
import pandas as pd
from scipy import spatial

class TravelCity:

    def __init__(self, travelcity_id, city, metro_centroid):
        self.id = travelcity_id
        self.city = city
        self.metro_centroid = metro_centroid
        self.passengers = []

class TravelCities:

    def __init__(self, commutecities):
        
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
