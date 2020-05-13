import numpy as np
import pandas as pd
from scipy import spatial

class TravelCityDistributor:

    def __init__(self, travelcities, msoas_coordinates):

        self.travelcities = travelcities
        self.msoa_coordinates = msoa_coordinates

        self._get_msoa_lat_lon()


    def _get_msoa_lat_lon(self):
        'Return all MSOA lat/lons as a 2D array'
       
        self.lat_msoas = np.array(self.msoa_coordinates['Y'])
        self.lon_msoas = np.array(self.msoa_coordinates['X'])
        self.msoas = np.array(self.msoa_coordinates['MSOA11CD'])
        
        lat_lon_msoas = np.zeros(len(self.lat_msoas)*2).reshape(len(self.lat_msoas),2)
        lat_lon_msoas[:,0] = self.lat_msoas
        lat_lon_msoas[:,1] = self.lon_msoas

        self.lat_lon_msoas = lat_lon_msoas

    def distribute_msoas(self):

        metro_centroids = []
        travel_cities = []
        for travelcity in self.travelcities:
            travel_cities.append(travelcity)
            metro_centroids.append(travelcity.metro_centroid)

        metro_centroids = np.array(metro_centroids)
        travel_cities = np.array(travel_cities)

        centroids_kd = spatial.KDTree(metro_centroids)

        for msoa in self.msoas:

            travel_cities[centroids_kd.query(msoa, 1)[1]].msoa = msoa

        
