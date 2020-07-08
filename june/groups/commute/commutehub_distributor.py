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

default_msoa_oa_coordinates = (
    paths.data_path / "input/geography/area_super_area_coordinates.csv"
)


class CommuteHubDistributor:
    """
    Distribute people to commute hubs based on where they live and where they are commuting to
    """

    def __init__(self, commutecities):

        self.commutecities = commutecities

    def _get_msoa_oa(self, area):
        "Get MSOA for a given OA"
        return self.coordinates_dict[area]["super_area"]

    def _get_area_lat_lon(self, oa):
        "Get lat/lon for  a given OA"
        area_dict = self.coordinates_dict[oa]
        return area_dict["latitude"], area_dict["longitude"]

    def from_file(self):

        coordinates_dict = dict()
        with open(default_msoa_oa_coordinates) as f:
            reader = csv.reader(f)
            headers = next(reader)
            key_index = headers.index("area")
            for row in reader:
                row_dict = dict(zip(headers, row))
                row_dict["longitude"] = float(row_dict["longitude"])
                row_dict["latitude"] = float(row_dict["latitude"])
                coordinates_dict[row[key_index]] = row_dict

        self.coordinates_dict = coordinates_dict

    def distribute_people(self):

        for commutecity in self.commutecities:
            # people commuting into city
            work_people = commutecity.people

            to_commute_in = []
            to_commute_out = []
            for work_person in work_people:

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

            for work_person in to_commute_out:
                live_area = work_person.area.name
                live_lat_lon = self._get_area_lat_lon(live_area)
                # find nearest commute hub to the person given where they live

                _, hub_index = commutehub_tree.query(live_lat_lon, 1)

                commutehub_in_city[hub_index].add(work_person)

            for work_person in to_commute_in:
                commutecity.commute_internal.append(work_person)
