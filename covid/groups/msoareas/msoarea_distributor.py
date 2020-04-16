import numpy as np
import pandas as pd
import os
from covid.groups.msoareas import MSOArea


class MSOAreaDistributor:
    def __init__(self, msoareas):
        self.msoareas = msoareas

    def read_msoareas_census(self):
        """
        Reads census data from the input dictionary, and initializes
        the encoders/decoders for company variables.
        It also initializes all the areas of the world.
        This is all on the MSOA layer.
        """
        msoareas_list = []
        msoa11cd = np.unique(self.msoareas.world.inputs.oa2msoa_df["MSOA11CD"].values)
        for i, msoa in enumerate(msoa11cd):
            msoarea = MSOArea(
                self.msoareas.world,
                msoa,
                self.msoareas.world.inputs.companysize_df.loc[msoa].values.sum(),
            )
            msoareas_list.append(msoarea)
        self.msoareas.members = msoareas_list 
        self.msoareas.ids_in_order = msoa11cd
