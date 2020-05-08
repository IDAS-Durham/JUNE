import numpy as np
import pandas as pd
from scipy import spatial
import matplotlib.pyplot as plt


class CommuteCity:
    """
    Defines a city with details about its metropolitan area and who commutes MSOAs within that area
    """

    def __init__(commutecity_id, city, metro_msoas, metro_centroid):
        """
        id: (int) id of the city
        metro_centriod: (array) the centriod of the metropolitan area
        metro_msoas: (list) names of all MSOAs in the metropolitain area of the city
        city: (string) name of the city
        passengers: (list) passengers commuting into any of the metropolitan MSOAs
                           - this includes those living AND working in the metropolitan area
        commutehubs: (list) commute hubs associated with the city
        """
        self.id = commutecity_id
        self.metro_centroid
        self.metro_msoas
        self.city
        self.passengers = []
        self.commutehubs = []

class CommuteCities:
    """
    Initialises commute cities by using postcode data on the station location
    and constructing metropolitan areas from these by expanding around their centriods

    Assumptions:
    - The metropolitan area is defined by the location of the major station in the city
    - We use the centriod of the MSOA where the station is to find the nearest 20 MSOAs
    - These are used to define the metropolitan area of the city
    - We then find the centriod of all the MSOAs to define the metropolitain area centroid
    - In the case of London where there are many major stations, we do this procedure for each station
      and define the London metropolitan area to be over the sum of all MSOAs near each station
    """

    def __init__(self, stat_pcs_df, is_london, uk_pcs_coordinates, msoa_coordinates):
        """
        stat_pcs_df: (pd.Dataframe) Dataframe containing the stations and their postcodes
        is_london: (bool) check if London
        uk_pcs_coodinates: (pd.Dataframe) Dataframe containing all UK postcodes and their coordinates
        msoa_coordinates: (pd.Dataframe) Dataframe containing all MSOA names and their coordinates
        members: (list) list of all commute cities

        Note: The London stat df is separate anc contains postcodes for all major Zone 1 stations in London
        Note: London must be initialised after the other stations
        """
        
        self.stat_pcs_df = stat_pcs_df
        self.is_london = is_london
        self.uk_pcs_coordinates = uk_pcs_coordinates
        self.msoa_coordinates = msoa_coordinates
        self.members = []

        # run to initialise all msoa lat lons from dataframe
        self._msoa_get_lat_lon()

        if self.is_london:
            if len(self.members) == 0:
                raise ValueError('London must be intialised after other stations')
            else:
                self.init_london()
        else:
            self.init_non_london()
        
    def _get_msoa_lat_lon(self):
        'Return all MSOA lat/lons as a 2D array'
       
        self.lat_msoas = np.array(self.msoa_coordinates['Y'])
        self.lon_msoas = np.array(self.msoa_coordinates['X'])
        self.msoas = np.array(self.msoa_coordinates['MSOA11CD'])
        
        lat_lon_msoas = np.zeros(len(lat_msoas)*2).reshape(len(lat_msoas),2)
        lat_lon_msoas[:,0] = lat_msoas
        lat_lon_msoas[:,1] = lon_msoas

        self.lon_lat_msoas = lon_lat_msoas

    def _get_stat_lat_lon(self, stat_pc):
        'Given a station postcode, return its lat/lon based on postcode data'

        pcs_stat = self.uk_pcs_coordinates[self.uk_pcs_coordinates['postcode'] == stat_pc]
        lat_stat = float(pcs_stat['latitude'])
        lon_stat = float(pcs_stat['longitude'])
        lat_lon_stat = [lat_stat, lon_stat]

        return lat_lon_stat


    def _get_msoa(self, lat_lon_stat):
        'Given the lat/lon of a station, get its MSOA and the MSOA lat/lon'
        
        lat_lon_msoa_stat = self.lat_lon_msoas[spatial.KDTree(self.lat_lon_msoas).query(lat_lon_stat)[1]]
        distance, index = spatial.KDTree(self.lat_lon_msoas).query(lat_lon_stat)
        msoa_stat = self.msoas[index]

        return lat_lon_msoa_stat, msoa_stat

    def _get_nearest_msoas(self,lat_lon_stat,nearest=20):
        'Given station lat/lon return 20 nearest MSOAs andd the centriod of all of these'

        metro_indices = spatial.KDTree(self.lat_lon_msoas).query(lat_lon_stat,nearest)[1]
        city_metro_lat_lon = self.lat_lon_msoas[indices]
        city_metro_msoas = self.msoas[metro_indices]
        city_metro_centroid = [np.mean(self.lat_msoas[metro_indices]),np.mean(self.lon_msoas[metro_indices])]
        
        return city_metro_msoas, city_metro_centroid
        
    def init_non_london(self):
        'Initialise non-London commute cities'

        stations = list(self.stat_pcs_df['station'])
        postcodes = list(self.stat_pcs_df['postcode'])
        
        for idx, stat_pc in enumerate(postcodes):

            # get lat/lon of station
            lat_lon_stat = self._get_lat_lon_stat(pcs_stat)

            # find nearest msoa
            lat_lon_stat, msoa_stat = self._get_msoa(lat_lon_stat)
            
            # find 20 nerest msoas to define metropolitan area
            city_metro_msoas, city_metro_centroid = self._get_nearest_msoas(lat_lon_stat)

            commute_city = CommuteCity(
                commutecity_id = idx,
                city = stations[idx],
                metro_msoas = city_metro_msoas,
                metro_centroid = city_metro_centroid
            )

            self.members.append(commute_city)


    def init_london(self):
        'Initialise London'

        stations = list(self.stat_pcs_df['station'])
        postcodes = list(self.stat_pcs_df['postcode'])

        city_metro_msoas_all = []
        city_metro_centroid_all = []
        for idx, stat_pc in enumerate(postcodes):

            # get lat/lon of station
            lat_lon_stat = self._get_lat_lon_stat(stat_pc)

            # find nearest msoa
            lat_lon_stat, msoa_stat = self._get_msoa(lat_lon_stat)

            # find 20 nerest msoas to local define metropolitan area
            city_metro_msoas, city_metro_centroid = self._get_nearest_msoas(lat_lon_stat)

            # run through all London stations and append all msoas and centriods to a list
            for i in city_metre_msoas:
                city_metro_msoas_all.append(i)
            city_metro_centroid_all.append(city_metro_centroid)

        # get global centroid
        city_metro_centroid_all = np.array(city_metro_centroid_all)
        city_metro_centroid = [np.mean(city_metro_centroid_all[:,0]), np.mean(city_metro_centroid_all[:,1])]

        commute_city = CommuteCity(
            commutecity_id = len(self.members)
            city = 'London',
            metro_msoas = city_metro_msoas_all,
            metro_centroid = city_metro_centroid
        )

        self.members.append(commute_city)
            
            
1
