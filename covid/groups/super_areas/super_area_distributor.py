import numpy as np
import pandas as pd
import os
from covid.groups.super_areas import SuperArea


class SuperAreaDistributor:
    def __init__(self, msoareas, relevant_groups):
        self.world = msoareas.world
        self.msoareas = msoareas
        self.relevant_groups = relevant_groups
        self.msoareas.names_in_order = np.unique(
                np.array([
                    area.super_area for area in self.world.areas.members
                    ])
                )
        mapping_df = self.msoareas.world.inputs.area_mapping_df
        # Search space reduction as we know where to look
        self.area_mapping_df = mapping_df[mapping_df["MSOA"].isin(self.msoareas.names_in_order)]
        self.create_super_areas()

    def create_super_areas(self):
        """
        Reads census data from the input dictionary, and initializes
        the encoders/decoders for company variables.
        It also initializes all the areas of the world.
        This is all on the super_area layer.
        """
        msoareas_list = []
        for msoa_name in self.msoareas.names_in_order:
            # centroid of msoa
            coordinates = ['xxx', 'xxx']
            # find postcode inside this msoarea
            pcd_in_msoa = self.area_mapping_df[
                self.area_mapping_df["MSOA"].isin([msoa_name])
            ]["PCD"].values
            # find oareas inside this msoarea
            oa_in_msoa = [
                area
                for area in self.world.areas.members
                if area.super_area == msoa_name
            ]
            # create msoarea
            msoarea = SuperArea(
                coordinates,
                oa_in_msoa,
                msoa_name,
                self.relevant_groups,
            )
            msoareas_list.append(msoarea)
            # link  area to msoarea
            for area in oa_in_msoa:
                area.super_area = msoarea
        self.msoareas.members = msoareas_list
