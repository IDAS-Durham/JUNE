import numpy as np
import pandas as pd
import os
from covid.groups.msoareas import MSOArea


class MSOAreaDistributor:
    def __init__(self, msoareas):
        self.msoareas = msoareas
        self.world = msoareas.world

    def read_msoareas_census(self):
        """
        Reads census data from the input dictionary, and initializes
        the encoders/decoders for company variables.
        It also initializes all the areas of the world.
        This is all on the MSOA layer.
        """
        msoareas_list = []
        msoa11cd = np.unique(self.msoareas.world.inputs.oa2msoa_df["MSOA11CD"].values)
        msoaofoa = np.array([
            [area.name, area.msoarea] for area in self.world.areas.members
        ]).T
        for i, msoa in enumerate(msoa11cd):
            # find oareas inside this msoa
            idxs = np.where(msoaofoa[1] == msoa)[0]
            areas = [self.world.areas.members[idx] for idx in idxs]
            # create msoarea
            msoarea = MSOArea(
                self.msoareas.world,
                msoa,
                areas,
            )
            msoareas_list.append(msoarea)
            # link  area to msoarea
            for area in areas:
                area.msoarea = msoarea
        self.msoareas.members = msoareas_list
        self.msoareas.ids_in_order = msoa11cd
