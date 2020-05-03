import pandas as pd
import os
from covid.groups.areas import OArea


class OAreaDistributor:
    def __init__(self, areas, input_data):
        self.world = areas.world
        self.areas = areas
        self.area_mapping_df = self.world.inputs.area_mapping_df
        self.input = input_data

    def read_areas_census(self):
        """
        Reads census data from the input dictionary, and initializes
        the encoders/decoders for sex, age, and household variables.
        It also initializes all the areas of the world.
        This is all on the OA layer.
        """
        n_residents_df = self.input.n_residents
        age_df = self.input.age_freq
        sex_df = self.input.sex_freq
        household_composition_df = self.input.household_composition_freq
        
        oa_in_sim = n_residents_df.index
        areas_list = []
        for i, oa_name in enumerate(oa_in_sim):
            # centroid of oarea
            coordinates = self.input.areas_coordinates_df.loc[oa_name][
                ["Y", "X"]
            ].values
            # find postcode inside this oarea
            pcd_in_oarea = self.area_mapping_df[
                self.area_mapping_df["OA"] == oa_name
            ]["PCD"].values
            # find belonging msoa
            msoa_name = self.area_mapping_df[
                self.area_mapping_df["OA"] == oa_name
            ]["MSOA"].unique()[0]
            # population estimate in the oarea
            census_freq = {
                "age_freq": age_df.loc[oa_name],
                "sex_freq": sex_df.loc[oa_name],
                "household_freq": household_composition_df.loc[oa_name],
            }
            area = OArea(
                self.world,
                coordinates,
                pcd_in_oarea,
                oa_name,
                msoa_name,
                n_residents_df.loc[oa_name],
                0,  # n_households_df.loc[oa_name],
                census_freq,
            )
            areas_list.append(area)
        self.areas.members = areas_list
        self.areas.names_in_order = oa_in_sim
