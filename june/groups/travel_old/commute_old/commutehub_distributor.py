#import logging
#import csv
#import numpy as np
#import pandas as pd
#
#from june import paths
#from scipy import spatial
#
#default_msoa_oa_coordinates = (
#    paths.data_path / "input/geography/area_super_area_coordinates.csv"
#)
#
#logger = logging.getLogger(__name__)
#
#
#class CommuteHubDistributor:
#    """
#    Distribute people to commute hubs based on where they live and where they are commuting to
#    """
#
#    def __init__(self, commutecities):
#
#        self.commutecities = commutecities
#
#    def _get_msoa_oa(self, area):
#        "Get MSOA for a given OA"
#        return self.coordinates_dict[area]["super_area"]
#
#    def _get_area_lat_lon(self, oa):
#        "Get lat/lon for  a given OA"
#        area_dict = self.coordinates_dict[oa]
#        return area_dict["latitude"], area_dict["longitude"]
#
#    def from_file(self):
#
#        coordinates_dict = {}
#        with open(default_msoa_oa_coordinates) as f:
#            reader = csv.reader(f)
#            headers = next(reader)
#            key_index = headers.index("area")
#            for row in reader:
#                row_dict = dict(zip(headers, row))
#                row_dict["longitude"] = float(row_dict["longitude"])
#                row_dict["latitude"] = float(row_dict["latitude"])
#                coordinates_dict[row[key_index]] = row_dict
#
#        self.coordinates_dict = coordinates_dict
#
#    def distribute_people(self):
#        logger.info(
#            f"Distributing people to commute hubs in {len(self.commutecities)} commute cities."
#        )
#        for commutecity in self.commutecities:
#            # people commuting into city
#            to_commute_in = []
#            to_commute_out = []
#            for commuter in commutecity.commuters:
#
#                msoa = self._get_msoa_oa(commuter.area.name)
#                # check if live AND work in metropolitan area
#                if msoa in commutecity.metro_msoas:
#                    to_commute_in.append(commuter)
#                # if they live outside and commute in then they need to commute through a hub
#                else:
#                    to_commute_out.append(commuter)
#
#            # possible commutehubs
#            commutehub_in_city = commutecity.commutehubs
#            commutehub_in_city_lat_lon = []
#            for commutehub in commutehub_in_city:
#                commutehub_in_city_lat_lon.append(commutehub.lat_lon)
#
#            commutehub_tree = spatial.KDTree(commutehub_in_city_lat_lon)
#            logger.info(
#                f"{commutecity.city} : {len(to_commute_in)} people commute in, " +\
#                f"{len(to_commute_out)} commute out."
#            )
#            for commuter in to_commute_out:
#                live_area = commuter.area.name
#                live_lat_lon = self._get_area_lat_lon(live_area)
#                # find nearest commute hub to the person given where they live
#
#                _, hub_index = commutehub_tree.query(live_lat_lon, 1)
#                commutehub_in_city[hub_index].add(commuter)
#
#            for commuter in to_commute_in:
#                commutecity.add_internal_commuter(commuter)
