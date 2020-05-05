import numpy as np
import pandas as pd
import os
from covid.groups.msoareas import MSOArea


class MSOAreaDistributor:
    def __init__(self, msoareas):
        self.world = msoareas.world
        self.msoareas = msoareas
        self.msoareas.names_in_order = np.unique(
                np.array([
                    area.msoarea for area in self.world.areas.members
                    ])
                )
        mapping_df = self.msoareas.world.inputs.area_mapping_df
        # Search space reduction as we know where to look
        self.area_mapping_df = mapping_df[mapping_df["MSOA"].isin(self.msoareas.names_in_order)]
        self.create_msoareas()

    def create_msoareas(self):
        """
        Reads census data from the input dictionary, and initializes
        the encoders/decoders for company variables.
        It also initializes all the areas of the world.
        This is all on the MSOA layer.
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
                if area.msoarea == msoa_name
            ]
            # create msoarea
            msoarea = MSOArea(
                self.world,
                coordinates,
                pcd_in_msoa,
                oa_in_msoa,
                msoa_name,
            )
            msoareas_list.append(msoarea)
            # link  area to msoarea
            for area in oa_in_msoa:
                area.msoarea = msoarea
        self.msoareas.members = msoareas_list
