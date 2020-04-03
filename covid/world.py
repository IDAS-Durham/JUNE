from covid.area import Area
from covid.inputs import Inputs
from sklearn.neighbors import BallTree
import pandas as pd

class World:
    """
    Stores global information about the simulation
    """
    def __init__(self):
        inputs  = Inputs() 
        self.people = {}
        self.total_people = 0
        self.decoder_sex = {}
        self.decoder_age = {}
        self.decoder_household_composition = {}
        self.areas = self.read_areas_census(inputs.household_dict)
        self.school_tree = self.create_school_tree(inputs.school_df)

    def create_school_tree(school_df):
        """
        Reads school location and sizes, it initializes a KD tree on a sphere,
        to query the closest schools to a given location.
        """
        school_tree = BallTree(np.deg2rad(school_df[['latitude', 'longitude']].values),
                                               metric='haversine')
        return school_tree

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

