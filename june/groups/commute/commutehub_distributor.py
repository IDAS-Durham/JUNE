import logging
import os
from enum import IntEnum
from pathlib import Path
from typing import List, Dict, Optional

import csv
import numpy as np
import pandas as pd

from june import paths
from scipy import spatial

default_geographical_data_directory = f"{paths.data_path}/geographical_data"
default_travel_data_directory = f"{paths.data_path}/travel"

default_file = f"{default_geographical_data_directory}/msoa_oa.csv"


default_data_path = (
    Path(os.path.abspath(__file__)).parent.parent.parent.parent
    / "data/"
)

default_msoa_oa_coordinates = default_data_path / "geographical_data/msoa_oa.csv"

class CommuteHubDistributor:
    """
    Distribute people to commute hubs based on where they live and where they are commuting to
    """

    def __init__(self, commutecities):

        #self.msoa_oa_coordinates = msoa_oa_coordinates
        self.commutecities = commutecities

    #def _get_msoa_oa(self,oa):
    #    'Get MSOA for a give OA'
    #    
    #    msoa = self.msoa_oa_coordinates['MSOA11CD'][self.msoa_oa_coordinates['OA11CD'] == oa]
    #
    #     return msoa

    def _get_msoa_oa(self, oa):
         'Get MSOA for a given OA'
         return self.coordinates_dict[
             oa
         ]["MSOA11CD"]

    def _get_area_lat_lon(self, oa):
        'Get lat/lon for  a given OA'
        #lat = float(self.msoa_oa_coordinates['Y'][self.msoa_oa_coordinates['OA11CD'] == oa])
        #lon = float(self.msoa_oa_coordinates['X'][self.msoa_oa_coordinates['OA11CD'] == oa])

        area_dict = self.coordinates_dict[
             oa
         ]
        return area_dict["Y"], area_dict["X"]

    def from_file(self):

        #self.msoa_oa_coordinates = pd.read_csv(default_msoa_oa_coordinates)

        coordinates_dict = dict()
        with open(default_msoa_oa_coordinates) as f:
            reader = csv.reader(f)
            headers = next(reader)
            key_index = headers.index("OA11CD")
            for row in reader:
                row_dict = dict(zip(
                    headers,
                    row
                ))
                row_dict["X"] = float(row_dict["X"])
                row_dict["Y"] = float(row_dict["Y"])
                coordinates_dict[row[key_index]] = row_dict
                
        self.coordinates_dict = coordinates_dict

    def distribute_people(self):

        for commutecity in self.commutecities:
            # people commuting into city
            work_people = commutecity.people

            # THIS IS GLACIALLY SLOW
            to_commute_in = []
            to_commute_out = []
            for work_person in work_people:
                #msoa = list(self._get_msoa_oa(work_person.area.name))[0]
                msoa = self._get_msoa_oa(work_person.area.name)
                # check if live AND work in metropolitan area
                if msoa in commutecity.metro_msoas:
                    to_commute_in.append(work_person)
                # if they live outside and commute in then they need to commute through a hub
                else:
                    to_commute_out.append(work_person)

            # possible commutehubs
            commutehub_in_city = commutecity.commutehubs
            commutehub_in_city_lat_lon = []
            for commutehub in commutehub_in_city:
                commutehub_in_city_lat_lon.append(commutehub.lat_lon)

            commutehub_tree = spatial.KDTree(commutehub_in_city_lat_lon)

            # THIS IS GLACIALLY SLOW
            for work_person in to_commute_out:
                live_area = work_person.area.name
                live_lat_lon = self._get_area_lat_lon(live_area)
                # find nearest commute hub to the person given where they live

                _, hub_index = commutehub_tree.query(live_lat_lon,1) 
                
                commutehub_in_city[hub_index].add(work_person,
                        activity_type=work_person.ActivityType.commute,
                        subgroup_type=commutehub_in_city[hub_index].SubgroupType.default
                        )

            for work_person in to_commute_in:
                commutecity.commute_internal.append(work_person)
