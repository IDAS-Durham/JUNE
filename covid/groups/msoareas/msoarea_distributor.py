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
        for i, msoa in enumerate(self.msoareas.world.inputs.companysize_df.index.values):
            msoarea = MSOArea(
                self.msoareas.world,
                msoa,
                self.msoareas.world.inputs.companysize_df.loc[msoa].sum(),
            )
            msoareas_list.append(msoarea)
        self.msoareas.members = msoareas_list 
