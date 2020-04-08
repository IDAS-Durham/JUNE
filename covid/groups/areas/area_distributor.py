import pandas as pd
import os
from covid.groups.areas import Area


class AreaDistributor:
    def __init__(self, areas, input_dict):
        self.input_dict = input_dict
        self.areas = areas

    def read_areas_census(self):
        """
        Reads census data from the input dictionary, and initializes
        the encoders/decoders for sex, age, and household variables.
        It also initializes all the areas of the world.
        This is all on the OA layer.
        """
        input_dict = self.input_dict
        # TODO: put this in input class
        areas_coordinates_df_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "..",
            "..",
            "..",
            "data",
            "geographical_data",
            "oa_coorindates.csv",
        )
        areas_coordinates_df = pd.read_csv(areas_coordinates_df_path)
        areas_coordinates_df.set_index("OA11CD", inplace=True)
        n_residents_df = input_dict.pop("n_residents")
        # n_households_df = input_dict.pop("n_households")
        age_df = input_dict.pop("age_freq")
        sex_df = input_dict.pop("sex_freq")
        household_compostion_df = input_dict.pop("household_composition_freq")
        for i, column in enumerate(age_df.columns):
            self.areas.decoder_age[i] = column
        for i, column in enumerate(sex_df.columns):
            self.areas.decoder_sex[i] = column
        for i, column in enumerate(household_compostion_df.columns):
            self.areas.decoder_household_composition[i] = column
            self.areas.encoder_household_composition[column] = i
        areas_dict = {}
        for i, area_name in enumerate(n_residents_df.index):
            area_coord = areas_coordinates_df.loc[area_name][["Y", "X"]].values
            area = Area(
                self.areas.world,
                area_name,
                n_residents_df.loc[area_name],
                0,  # n_households_df.loc[area_name],
                {
                    "age_freq": age_df.loc[area_name],
                    "sex_freq": sex_df.loc[area_name],
                    "household_freq": household_compostion_df.loc[area_name],
                },
                area_coord,
            )
            areas_dict[i] = area
        self.areas.members = areas_dict
