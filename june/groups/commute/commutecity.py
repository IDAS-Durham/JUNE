import numpy as np
import pandas as pd
from scipy import spatial
from june.demography.geography import Geography, SuperArea
from june.groups.group import Group, Supergroup
from june import paths

default_data_path = paths.data_path

default_uk_pcs_coordinates = default_data_path / "input/geography/postcodes_coordinates.csv"

default_msoa_coordinates = default_data_path / "input/geography/super_area_coordinates.csv"

default_non_london_stat_pcs = default_data_path / "input/travel/non_London_station_coordinates.csv"

default_london_stat_pcs = default_data_path / "input/travel/London_station_coordinates.csv"

class CommuteError(BaseException):
    pass

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

    def __init__(self, commutecities: List["CommuteCities"]):
        """
        uk_pcs_coodinates: (pd.Dataframe) Dataframe containing all UK postcodes and their coordinates
        msoa_coordinates: (pd.Dataframe) Dataframe containing all MSOA names and their coordinates
        members: (list) list of all commute cities

        Note: The London stat df is separate anc contains postcodes for all major Zone 1 stations in London
        Note: London must be initialised after the other stations
        """
        
        super().__init__()
        self.members = commutecities

    @classmethod
    def for_geography(
            cls,
            geography: Geography,
            uk_pcs_coordinate_file: str = default_uk_coordinates,
            msoa_coordinates_file: str = default_msoa_coordinates,
            london_stat_pcs_file: str = default_london_stat_pcs,
            non_london_stat_pcs_file: str = default_non_london_stat_pcs,
            
    ):
        if not geography.super_areas:
            raise CommuteError("Empty geography!")
        return cls.for_super_areas(
            geography.super_areas,
            uk_pcs_coordinates_file,
            msoa_coordinates_file,
            london_stat_pcs_file,
            non_london_stat_pcs_file,
        )

    @classmethod
    def for_super_areas(
            cls,
            super_areas: List[SuperArea],
            uk_pcs_coordinate_file: str = default_uk_coordinates,
            msoa_coordinates_file: str = default_msoa_coordinates,
            london_stat_pcs_file: str = default_london_stat_pcs,
            non_london_stat_pcs_file: str = default_non_london_stat_pcs,
    ):
        
        uk_pcs_coordinates = pd.read_csv(uk_pcs_coordinates_file)
        msoa_coordinates = pd.read_csv(msoa_coordinates_file)

        lat_msoas, lon_msoas, lat_lon_msoas = get_msoa_lat_lon(msoa_coordinates)

        # initialise non-London stations
        stat_pcs_df = pd.read_csv(default_non_london_stat_pcs)
        stations = list(stat_pcs_df['station'])
        postcodes = list(stat_pcs_df['postcode'])

        members = []
        for idx, stat_pc in enumerate(postcodes):

            # get lat/lon of station
            lat_lon_stat = get_stat_lat_lon(stat_pc, uk_pcs_coordinates)

            # find nearest msoa
            lat_lon_stat, msoa_stat = get_msoa(lat_lon_stat, lat_lon_msoas, msoas)

            super_area_stat = None
            for super_area in super_areas:
                if super_area.name == msoa_stat:
                    super_area_stat = super_area
                    break
            
            # find 20 nerest msoas to define metropolitan area
            city_metro_msoas, city_metro_centroid = get_nearest_msoas(lat_lon_stat, lat_lon_msoas, msoas, lat_msoas, lon_msoas)

            
            commute_city = CommuteCity(
                city = stations[idx],
                super_area = super_area_stat,
                metro_msoas = city_metro_msoas,
                metro_centroid = city_metro_centroid,
            )

            members.append(commute_city)

        # initialise London stations
        stat_pcs_df = pd.read_csv(default_london_stat_pcs)
        stations = list(stat_pcs_df['station'])
        postcodes = list(stat_pcs_df['postcode'])

        city_metro_msoas_all = []
        city_metro_centroid_all = []
        for idx, stat_pc in enumerate(postcodes):

            # get lat/lon of station
            lat_lon_stat = get_stat_lat_lon(stat_pc, uk_pcs_coordinates)

            # find nearest msoa
            lat_lon_stat, msoa_stat = get_msoa(lat_lon_stat, lat_lon_msoas, msoas)

            # find 20 nerest msoas to local define metropolitan area
            city_metro_msoas, city_metro_centroid = get_nearest_msoas(lat_lon_stat, lat_lon_msoas, msoas, lat_msoas, lon_msoas)

            # run through all London stations and append all msoas and centriods to a list
            for i in city_metro_msoas:
                city_metro_msoas_all.append(i)
            city_metro_centroid_all.append(city_metro_centroid)

        # get global centroid
        city_metro_centroid_all = np.array(city_metro_centroid_all)
        city_metro_centroid = [np.mean(city_metro_centroid_all[:,0]), np.mean(city_metro_centroid_all[:,1])]
        msoa_stat, _ = get_nearest_msoas(city_metro_centroid, lat_lon_msoas, msoas, lat_msoas, lon_msoas, nearest=1)

        super_area_stat = None
            for super_area in super_areas:
                if super_area.name == msoa_stat:
                    super_area_stat = super_area
                    break
        
        commute_city = CommuteCity(
            city = 'London',
            super_area = super_area_stat,
            metro_msoas = city_metro_msoas_all,
            metro_centroid = city_metro_centroid,
        )

        members.append(commute_city)

        return cls(members)
        

    # def init_non_london(self):
    #     """
    #     Initialise non-London commute cities
    #     stat_pcs_df: (pd.Dataframe) Dataframe containing the stations and their postcodes
    #     """

    #     self.stat_pcs_df = pd.read_csv(default_non_london_stat_pcs)
        
    #     stations = list(self.stat_pcs_df['station'])
    #     postcodes = list(self.stat_pcs_df['postcode'])
        
    #     for idx, stat_pc in enumerate(postcodes):

    #         # get lat/lon of station
    #         lat_lon_stat = self._get_stat_lat_lon(stat_pc)

    #         # find nearest msoa
    #         lat_lon_stat, msoa_stat = self._get_msoa(lat_lon_stat)
            
    #         # find 20 nerest msoas to define metropolitan area
    #         city_metro_msoas, city_metro_centroid = self._get_nearest_msoas(lat_lon_stat)

    #         commute_city = CommuteCity(
    #             city = stations[idx],
    #             super_area = msoa_stat,
    #             metro_msoas = city_metro_msoas,
    #             metro_centroid = city_metro_centroid,
    #         )

    #         self.members.append(commute_city)


    # def init_london(self):
    #     """
    #     Initialise London
    #     stat_pcs_df: (pd.Dataframe) Dataframe containing the stations and their postcodes
    #     """

    #     self.stat_pcs_df = pd.read_csv(default_london_stat_pcs)
        
    #     stations = list(self.stat_pcs_df['station'])
    #     postcodes = list(self.stat_pcs_df['postcode'])

    #     city_metro_msoas_all = []
    #     city_metro_centroid_all = []
    #     for idx, stat_pc in enumerate(postcodes):

    #         # get lat/lon of station
    #         lat_lon_stat = self._get_stat_lat_lon(stat_pc)

    #         # find nearest msoa
    #         lat_lon_stat, msoa_stat = self._get_msoa(lat_lon_stat)

    #         # find 20 nerest msoas to local define metropolitan area
    #         city_metro_msoas, city_metro_centroid = self._get_nearest_msoas(lat_lon_stat)

    #         # run through all London stations and append all msoas and centriods to a list
    #         for i in city_metro_msoas:
    #             city_metro_msoas_all.append(i)
    #         city_metro_centroid_all.append(city_metro_centroid)

    #     # get global centroid
    #     city_metro_centroid_all = np.array(city_metro_centroid_all)
    #     city_metro_centroid = [np.mean(city_metro_centroid_all[:,0]), np.mean(city_metro_centroid_all[:,1])]
    #     metro_stat = self._get_nearest_msoas(city_metro_centroid, nearest=1)
        
    #     commute_city = CommuteCity(
    #         city = 'London',
    #         super_area = msoa_stat,
    #         metro_msoas = city_metro_msoas_all,
    #         metro_centroid = city_metro_centroid,
    #     )

    #     self.members.append(commute_city)

def get_msoa_lat_lon(msoa_coordinates):
    'Return all MSOA lat/lons as a 2D array'
        
    lat_msoas = np.array(msoa_coordinates['latitude'])
    lon_msoas = np.array(msoa_coordinates['longitude'])
    msoas = np.array(msoa_coordinates['super_area'])
    
    lat_lon_msoas = np.zeros(len(lat_msoas)*2).reshape(len(lat_msoas),2)
    lat_lon_msoas[:,0] = lat_msoas
    lat_lon_msoas[:,1] = lon_msoas

    return lat_msoas, lon_msoas, lat_lon_msoas

def get_stat_lat_lon(stat_pc, uk_pcs_coordinates):
    'Given a station postcode, return its lat/lon based on postcode data'

    pcs_stat = uk_pcs_coordinates[uk_pcs_coordinates['postcode'] == stat_pc]
    lat_stat = float(pcs_stat['latitude'])
    lon_stat = float(pcs_stat['longitude'])
    lat_lon_stat = [lat_stat, lon_stat]

    return lat_lon_stat

def get_msoa(lat_lon_stat, lat_lon_msoas, msoas):
    'Given the lat/lon of a station, get its MSOA and the MSOA lat/lon'
        
    lat_lon_msoa_stat = lat_lon_msoas[spatial.KDTree(lat_lon_msoas).query(lat_lon_stat)[1]]
    distance, index = spatial.KDTree(lat_lon_msoas).query(lat_lon_stat)
    msoa_stat = msoas[index]
    
    return lat_lon_msoa_stat, msoa_stat

def get_nearest_msoas(lat_lon_stat, lat_lon_msoas, msoas, lat_msoas, lon_msoas, nearest=20):
    'Given station lat/lon return 20 nearest MSOAs andd the centriod of all of these'

    metro_indices = spatial.KDTree(lat_lon_msoas).query(lat_lon_stat,nearest)[1]
    city_metro_lat_lon = lat_lon_msoas[metro_indices]
    city_metro_msoas = msoas[metro_indices]
    city_metro_centroid = [np.mean(lat_msoas[metro_indices]),np.mean(lon_msoas[metro_indices])]
        
    return city_metro_msoas, city_metro_centroid
    
