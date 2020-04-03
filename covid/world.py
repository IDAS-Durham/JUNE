from sklearn.neighbors import BallTree
from covid.inputs import Inputs
from covid.area import Area
from covid.distributors import *
import pandas as pd
import numpy as np
from tqdm import tqdm # for a fancy progress bar

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
        self.encoder_household_composition = {}
        self.decoder_household_composition = {}
        self.areas = self.read_areas_census(inputs.household_dict)
        self.primary_school_tree = self.create_school_tree(inputs.school_df)

    def create_school_tree(self,school_df):
        """
        Reads school location and sizes, it initializes a KD tree on a sphere,
        to query the closest schools to a given location.
        """
        school_tree = BallTree(np.deg2rad(school_df[['latitude', 'longitude']].values),
                                               metric='haversine')
        return school_tree

    def read_areas_census(self, input_dict):
        """
        Reads census data from the input dictionary, and initializes
        the encoders/decoders for sex, age, and household variables.
        It also initializes all the areas of the world.
        """
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

    def populate_world(self):
        """
        Populates world with people, houses, schools, etc.
        """
        print("creating world...")
        pbar = tqdm(total=len(self.areas.keys()))  # progress bar
        for area in self.areas.values():
            # create population
            people_dist = PeopleDistributor(area)
            people_dist.populate_area()

            # distribute people to households
            household_dist = HouseholdDistributor(area)
            household_dist.distribute_people_to_household()

            # distribute kids to schools
            school_dist = SchoolDistributor(area)
            school_dist.distribute_kids_to_school() 

            pbar.update(1)
        pbar.close()

