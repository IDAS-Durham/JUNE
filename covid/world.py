from covid.area import Area
from sklearn.neighbors import BallTree
import pandas as pd
import numpy as np

class World:
    """
    Stores global information about the simulation
    """
    def __init__(self, input_dict):
        self.people = {}
        self.total_people = 0
        self.decoder_sex = {}
        self.decoder_age = {}
        self.decoder_household_composition = {}
        self.encoder_household_composition = {}
        self.areas = self.read_areas_census(input_dict)
        self.schools = self.read_school_census()
        print(self.encoder_household_composition)

    def read_school_census(self):
        """
        Reads school location and sizes, it initializes a KD tree on a sphere,
        to query the closest schools to a given location.
        """
        school_data = pd.read_csv("../data/census_data/school_data/england_schools_data.csv")
        self.school_tree = BallTree(np.deg2rad(school_data[['latitude', 'longitude']].values),
                                               metric='haversine')

    def read_areas_census(self, input_dict):
        n_residents_df = input_dict.pop("n_residents")
        n_households_df = input_dict.pop("n_households")
        age_df = input_dict.pop("age_freq")
        sex_df = input_dict.pop("sex_freq")
        household_compostion_df = input_dict.pop("household_composition_freq")
        for i, column in enumerate(age_df.columns):
            self.decoder_age[i] = column
        for i, column in enumerate(sex_df.columns):
            self.decoder_sex[i] = column
        for i, column in enumerate(household_compostion_df.columns):
            self.decoder_household_composition[i] = column
            self.encoder_household_composition[column] = i
        areas_dict = {}
        for i, area_name in enumerate(n_residents_df.index):
            area = Area(self,
                                area_name,
                                n_residents_df.loc[area_name],
                                n_households_df.loc[area_name],
                                {
                                    "age_freq": age_df.loc[area_name],
                                    "sex_freq" : sex_df.loc[area_name],
                                    "household_freq": household_compostion_df.loc[area_name]
                                }
                                )
            areas_dict[i] = area
        return areas_dict

