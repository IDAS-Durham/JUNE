import numpy as np
import pandas as pd
from scipy import spatial
import matplotlib.pyplot as plt


class CommuteCity():

    def __init__(commutecity_id, city, metro_msoas, metro_centroid):
        self.id = commutecity_id
        self.metro_centroid # latitude/longitude of metro centroid
        self.metro_msoas # msoas belonging to metro area
        self.city
        self.passengers = [] # people commuting to the city

class CommuteCities():

    def __init__(self, stat_pcs_df, is_london, uk_pcs_coordinates, msoa_coordinates):
        self.stat_pcs_df = stat_pcs_df
        self.is_london = is_london
        self.uk_pcs_coordinates = uk_pcs_coordinates
        self.msoa_coordinates = msoa_coordinates
        self.members = []

        if self.is_london:
            self.init_london
        else:
            self.init_non_london
        
    def init_non_london(self):
        stations = list(self.stat_pcs_df['station'])
        postcodes = list(self.stat_pcs_df['postcode'])

        lat_msoas = np.array(self.msoa_coordinates['Y'])
        lon_msoas = np.array(self.msoa_coordinates['X'])
        msoas = np.array(self.msoa_coordinates['MSOA11CD'])
        
        lat_lon_msoas = np.zeros(len(lat_msoas)*2).reshape(len(lat_msoas),2)
        lat_lon_msoas[:,0] = lat_msoas
        lat_lon_msoas[:,1] = lon_msoas
        
        for idx, stat_pc in emumerate(postcodes):

            # get lat/lon of station
            pcs_stat = self.uk_pcs_coordinates[self.uk_pcs_coordinates['postcode'] == stat_pc]
            lat_stat = float(pcs_stat['latitude'])
            lon_stat = float(pcs_stat['longitude'])
            lat_lon_stat = [lat_stat, lon_stat]

            # find nearest msoa
            lat_lon_msoa_stat = lat_lon_msoas[spatial.KDTree(lat_lon_msoas).query(lat_lon_stat)[1]]
            distance, index = spatial.KDTree(lat_lon_msoas).query(lat_lon_stat)
            msoa_stat = msoas[index]
            
            # find 20 nerest msoas to define metropolitan area
            metro_indices = spatial.KDTree(lat_lon_msoas).query(lat_lon_stat,20)[1]
            city_metro_lat_lon = lat_lon_msoas[indices]
            city_metro_msoas = msoas[metro_indices]
            city_metro_centroid = [np.mean(lat_msoas[metro_indices]),np.mean(lon_msoas[metro_indices])]

            commute_city = CommuteCity(
                commutecity_id = idx,
                city = stations[idx],
                metro_mdoas = city_metro_msoas
                metro_centroid = city_metro_centroid
            )

            self.members.append(commute_city)

    
            
