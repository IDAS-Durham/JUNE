import numpy as np
import pandas as pd
import os
from covid.groups.msoareas import MSOArea


class MSOAreaDistributor:
    def __init__(self, msoareas):
        self.msoareas = msoareas
        self.area_mapping_df = self.msoareas.world.inputs.area_mapping_df

    def read_msoareas_census(self):
        """
        Reads census data from the input dictionary, and initializes
        the encoders/decoders for company variables.
        It also initializes all the areas of the world.
        This is all on the MSOA layer.
        """
        msoareas_list = []
        msoa_in_sim = self.area_mapping_df["MSOA"].unique()
        for msoa in msoa_in_sim:
            msoarea = MSOArea(
                self.msoareas.world,
                msoa,
                self.msoareas.world.inputs.companysize_df.loc[msoa].values.sum(),
            )
            msoareas_list.append(msoarea)
        self.msoareas.members = msoareas_list
        self.msoareas.names_in_order = msoa_in_sim
