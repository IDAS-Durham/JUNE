import numpy as np
import pandas as pd
from scipy import spatial

class TravelCityDistributor:

    def __init__(self, travelcities, msoas):

        self.travelcities = travelcities
        self.msoa_coordinates = msoa_coordinates

        self._get_msoa_lat_lon()
        self._get_msoa_names()


    def _get_msoa_lat_lon(self):
        'Return all MSOA lat/lons as a 2D array'

        lat_lon_msoas = []
        msoa_names = []
        for msoa in self.msoas:
            lat_lon_msoas.append(msoa.coordinates)
            msoa_names.append(msoa.name)
        
        self.lat_lon_msoas = lat_lon_msoas
        self.msoa_names = msoa_names

    def _get_msoa_names(self):

        msoa_names = []
        for msoa in self.msoas:
            msoa_names.append(msoa.name)

        self.msoa_names = np.array(msoa_names)

    def distribute_msoas(self):

        metro_centroids = []
        travel_cities = []
        for travelcity in self.travelcities:
            travel_cities.append(travelcity)
            metro_centroids.append(travelcity.metro_centroid)

        metro_centroids = np.array(metro_centroids)
        travel_cities = np.array(travel_cities)

        centroids_kd = spatial.KDTree(metro_centroids)

        for idx, msoa_coord in enumerate(self.lat_lon_msoas):

            # append msoa class to travel_cities
            travel_cities[centroids_kd.query(msoa_coord, 1)[1]].msoa = self.msoas[idx]

        
