import pandas as pd
import os
from covid.groups.areas import OArea


class OAreaDistributor:
    def __init__(self, areas, input_data):
        self.world = areas.world
        self.areas = areas
        self.input = input_data
        mapping_df = self.areas.world.inputs.area_mapping_df
        # Reduce to the OA that are required --- reduces the search space later
        self.area_mapping_df = mapping_df[mapping_df["OA"].isin(self.input.n_residents.index)]

    def get_area_coord(self, oarea_name):
        """
        Read two numbers from input df, return as array.
        """
        import numpy as np
        df_entry = self.input.areas_coordinates_df.loc[oarea_name]
        # NOTE df["X"] ~5 times faster than df[ ["Y", "X"] ]
        # FIXME explicit conversion to np.array necessary?
        return [df_entry["Y"], df_entry["X"]]

    def areaname_to_msoa(self, oarea_name):
        """
        Find and return MSOA that corresponds to area_name.
        """
        # NOTE df["OA"] == area_name ~factor 2 slower than df["OA"].isin([area_name])
        return self.area_mapping_df[
            self.area_mapping_df["OA"].isin([oarea_name])
        ]["MSOA"].unique()[0]

    def mk_area(self, oarea_name):
        area = OArea(
            self.areas.world,
            self.get_area_coord(oarea_name),
            oarea_name,
            self.areaname_to_msoa(oarea_name),
            self.input.n_residents.loc[oarea_name],
            0,  # n_households_df.loc[area_name],
            {
                "age_freq": self.input.age_freq.loc[oarea_name],
                "sex_freq": self.input.sex_freq.loc[oarea_name],
                "household_freq": self.input.household_composition_freq.loc[oarea_name],
            },
        )
        return area

    def read_areas_census(self):
        """
        Reads census data from the input dictionary, and initializes
        the encoders/decoders for sex, age, and household variables.
        It also initializes all the areas of the world.
        This is all on the OA layer.
        """
        areas_list = []
        oa_in_sim = self.input.n_residents.index
        import time
        t0 = time.time()
        ## This could be done in parallel
        for i, oarea_name in enumerate(oa_in_sim):
            if (i+1)%100 == 0:
                print(
                    "{}/{} freq: {} Hz".format(
                        i+1, len(oa_in_sim), (i+1)/(time.time()-t0)
                    ),
                    end="\r",
                )
            areas_list.append(self.mk_area(oarea_name))
        self.areas.members = areas_list
        self.areas.names_in_order = oa_in_sim
