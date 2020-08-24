
import numpy as np
import pandas as pd
from scipy import spatial
from june.groups.group import Group, Supergroup
from june import paths

default_data_path = paths.data_path

default_uk_pcs_coordinates = default_data_path / "input/geography/postcodes_coordinates.csv"

default_msoa_coordinates = default_data_path / "input/geography/super_area_coordinates.csv"

default_non_london_stat_pcs = default_data_path / "input/travel/non_London_station_coordinates.csv"

default_london_stat_pcs = default_data_path / "input/travel/London_station_coordinates.csv"

class CommuteCity(Group):
    """
    Defines a city with details about its metropolitan area and who commutes MSOAs within that area.
    """

    __slots__ = (
        "id",
        "metro_centroid",
        "metro_msoas",
        "city",
        "super_area",
        "commutehubs",
        "commute_internal",
        "commutecityunits",
    )

    
    def __init__(self, city=None, super_area=None, metro_msoas=None, metro_centroid=None):
        """
        metro_centriod: (array) the centriod of the metropolitan area
        metro_msoas: (list) names of all MSOAs in the metropolitain area of the city
        city: (string) name of the city
        people: (Group attribute) passengers commuting into any of the metropolitan MSOAs
                           - this includes those living AND working in the metropolitan area
        commutehubs: (list) commute hubs associated with the city
        commute_internal: (list) people who live and work in the metro_msoas
        commutecityunits: (list) units associated with commute_internal persons
        """
        super().__init__()
        
        self.metro_centroid = metro_centroid
        self.metro_msoas = metro_msoas
        self.city = city
        self.super_area = super_area
        self.commutehubs = []
        self.commute_internal = []
        self.commutecityunits = []

class CommuteCities(Supergroup):
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

    def __init__(self):
        """
        uk_pcs_coodinates: (pd.Dataframe) Dataframe containing all UK postcodes and their coordinates
        msoa_coordinates: (pd.Dataframe) Dataframe containing all MSOA names and their coordinates
        members: (list) list of all commute cities

        Note: The London stat df is separate anc contains postcodes for all major Zone 1 stations in London
        Note: London must be initialised after the other stations
        """
        
        super().__init__()
        self.members = []
        
        
    def _get_msoa_lat_lon(self):
        'Return all MSOA lat/lons as a 2D array'
       
        self.lat_msoas = np.array(self.msoa_coordinates['latitude'])
        self.lon_msoas = np.array(self.msoa_coordinates['longitude'])
        self.msoas = np.array(self.msoa_coordinates['super_area'])
        
        lat_lon_msoas = np.zeros(len(self.lat_msoas)*2).reshape(len(self.lat_msoas),2)
        lat_lon_msoas[:,0] = self.lat_msoas
        lat_lon_msoas[:,1] = self.lon_msoas

        self.lat_lon_msoas = lat_lon_msoas

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
        city_metro_lat_lon = self.lat_lon_msoas[metro_indices]
        city_metro_msoas = self.msoas[metro_indices]
        city_metro_centroid = [np.mean(self.lat_msoas[metro_indices]),np.mean(self.lon_msoas[metro_indices])]
        
        return city_metro_msoas, city_metro_centroid

    def from_file(self):
        
        self.uk_pcs_coordinates = pd.read_csv(default_uk_pcs_coordinates)
        self.msoa_coordinates = pd.read_csv(default_msoa_coordinates)

        # run to initialise all msoa lat lons from dataframe
        self._get_msoa_lat_lon()
        
    def init_non_london(self):
        """
        Initialise non-London commute cities
        stat_pcs_df: (pd.Dataframe) Dataframe containing the stations and their postcodes
        """

        self.stat_pcs_df = pd.read_csv(default_non_london_stat_pcs)
        
        stations = list(self.stat_pcs_df['station'])
        postcodes = list(self.stat_pcs_df['postcode'])
        
        for idx, stat_pc in enumerate(postcodes):

            # get lat/lon of station
            lat_lon_stat = self._get_stat_lat_lon(stat_pc)

            # find nearest msoa
            lat_lon_stat, msoa_stat = self._get_msoa(lat_lon_stat)
            
            # find 20 nerest msoas to define metropolitan area
            city_metro_msoas, city_metro_centroid = self._get_nearest_msoas(lat_lon_stat)

            commute_city = CommuteCity(
                city = stations[idx],
                super_area = msoa_stat
                metro_msoas = city_metro_msoas,
                metro_centroid = city_metro_centroid,
            )

            self.members.append(commute_city)


    def init_london(self):
        """
        Initialise London
        stat_pcs_df: (pd.Dataframe) Dataframe containing the stations and their postcodes
        """

        self.stat_pcs_df = pd.read_csv(default_london_stat_pcs)
        
        stations = list(self.stat_pcs_df['station'])
        postcodes = list(self.stat_pcs_df['postcode'])

        city_metro_msoas_all = []
        city_metro_centroid_all = []
        for idx, stat_pc in enumerate(postcodes):

            # get lat/lon of station
            lat_lon_stat = self._get_stat_lat_lon(stat_pc)

            # find nearest msoa
            lat_lon_stat, msoa_stat = self._get_msoa(lat_lon_stat)

            # find 20 nerest msoas to local define metropolitan area
            city_metro_msoas, city_metro_centroid = self._get_nearest_msoas(lat_lon_stat)

            # run through all London stations and append all msoas and centriods to a list
            for i in city_metro_msoas:
                city_metro_msoas_all.append(i)
            city_metro_centroid_all.append(city_metro_centroid)

        # get global centroid
        city_metro_centroid_all = np.array(city_metro_centroid_all)
        city_metro_centroid = [np.mean(city_metro_centroid_all[:,0]), np.mean(city_metro_centroid_all[:,1])]
        metro_stat = self._get_nearest_msoas(city_metro_centroid, nearest=1)
        
        commute_city = CommuteCity(
            city = 'London',
            super_area = msoa_stat
            metro_msoas = city_metro_msoas_all,
            metro_centroid = city_metro_centroid,
        )

        self.members.append(commute_city)
