import pandas as pd
import numpy as np
import os
from covid.groups.areas import Area
from sklearn.neighbors._ball_tree import BallTree


class AreaDistributor:
    def __init__(self, areas, input_data):
        self.input = input_data
        self.areas = areas
        mapping_df = self.areas.world.inputs.area_mapping_df
        # Reduce to the OA that are required --- reduces the search space later
        self.area_mapping_df = mapping_df[mapping_df["OA"].isin(self.input.n_residents.index)]

    def get_area_coord(self, area_name):
        """
        Read two numbers from input df, return as array.
        """
        import numpy as np
        df_entry = self.input.areas_coordinates_df.loc[area_name]
        # NOTE df["X"] ~5 times faster than df[ ["Y", "X"] ]
        # FIXME explicit conversion to np.array necessary?
        return np.array([df_entry["Y"], df_entry["X"]])

    def areaname_to_msoa(self, area_name):
        """
        Find and return MSOA that corresponds to area_name.
        """
        # NOTE df["OA"] == area_name ~factor 2 slower than df["OA"].isin([area_name])
        return self.area_mapping_df[ self.area_mapping_df["OA"].isin([area_name])  ]["MSOA"].unique()[0]

    def mk_area(self, area_name):
        area = Area(
            self.areas.world,
            area_name,
            self.areaname_to_msoa(area_name),
            self.input.n_residents.loc[area_name],
            0,  # n_households_df.loc[area_name],
            {
                "age_freq": self.input.age_freq.loc[area_name],
                "sex_freq": self.input.sex_freq.loc[area_name],
                "household_freq": self.input.household_composition_freq.loc[area_name],
            },
            self.get_area_coord(area_name),
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
        for i, area_name in enumerate(oa_in_sim):
            if (i+1)%100 == 0:
                print("{}/{} freq: {} Hz".format(i+1, len(oa_in_sim), (i+1)/(time.time()-t0)), end="\r")
            areas_list.append(self.mk_area(area_name))
        self.areas.members = areas_list
        self.areas.names_in_order = oa_in_sim
        self.areas.area_tree = BallTree(
            np.deg2rad(self.input.areas_coordinates_df[["Y", "X"]].values),
            metric="haversine"
        )
