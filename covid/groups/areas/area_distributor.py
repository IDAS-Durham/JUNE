import pandas as pd
import os
from covid.groups.areas import Area


class AreaDistributor:
    def __init__(self, areas, input_data):
        self.input = input_data
        self.areas = areas
        self.area_mapping_df = self.areas.world.inputs.area_mapping_df

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
        areas_list = []
        for i, area_name in enumerate(n_residents_df.index):
            area_coord = self.input.areas_coordinates_df.loc[area_name][
                ["Y", "X"]
            ].values
            area = Area(
                self.areas.world,
                area_name,
                self.area_mapping_df[
                    self.area_mapping_df["OA"] == area_name
                ]["MSOA"].unique()[0],
                n_residents_df.loc[area_name],
                0,  # n_households_df.loc[area_name],
                {
                    "age_freq": age_df.loc[area_name],
                    "sex_freq": sex_df.loc[area_name],
                    "household_freq": household_composition_df.loc[area_name],
                },
                area_coord,
            )
            areas_list.append(area)
        self.areas.members = areas_list
