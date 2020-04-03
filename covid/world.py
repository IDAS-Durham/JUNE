from sklearn.neighbors import BallTree
from covid.inputs import Inputs
from covid.area import Area
from covid.distributors import *
from covid.school import School
import pandas as pd
import numpy as np
from tqdm import tqdm  # for a fancy progress bar


class World:
    """
    Stores global information about the simulation
    """

    def __init__(self):
        inputs = Inputs()
        self.people = {}
        self.total_people = 0
        self.decoder_sex = {}
        self.decoder_age = {}
        self.encoder_household_composition = {}
        self.decoder_household_composition = {}
        self.areas = self.read_areas_census(inputs.household_dict)
        self.primary_schools, self.primary_schools_tree = self._init_schools(
            inputs.primary_school
        )
        self.secondary_schools, self.secondary_schools_tree = self._init_schools(
            inputs.secondary_school
        )
        # self.secondary_school_tree = self.create_school_tree(inputs.secondary_school)

    def _init_schools(self, school_df):
        """
        Initializes schools.
        """
        schools = {}
        school_tree = self._create_school_tree(school_df)
        for i, (index, row) in enumerate(school_df.iterrows()):
            school = School(
                i,
                np.array(row[["latitude", "longitude"]].values, dtype=np.float64),
                row["NOR"],
                row["URN"],
            )
            schools[i] = school
        return schools, school_tree

    def get_closest_primary_schools(self, area, k=1):
        """
        Returns the k schools closest to the output area centroid.
        """
        dist, neighbors = self.primary_schools_tree.query(
            np.deg2rad(area.coordinates.reshape(1, -1)), k=k
        )
        return neighbors[0]

    def get_closest_secondary_schools(self, area, k=1):
        """
        Returns the k schools closest to the output area centroid.
        """
        dist, neighbors = self.secondary_schools_tree.query(
            np.deg2rad(area.coordinates.reshape(1, -1)), k=k
        )
        return neighbors[0]

    def _create_school_tree(self, school_df):
        """
        Reads school location and sizes, it initializes a KD tree on a sphere,
        to query the closest schools to a given location.
        """
        school_tree = BallTree(
            np.deg2rad(school_df[["latitude", "longitude"]].values), metric="haversine"
        )
        return school_tree

    def read_areas_census(self, input_dict):
        """
        Reads census data from the input dictionary, and initializes
        the encoders/decoders for sex, age, and household variables.
        It also initializes all the areas of the world.
        """
        # TODO: put this in input class
        areas_coordinates_df = pd.read_csv(
            "../data/geographical_data/oa_coorindates.csv"
        )
        areas_coordinates_df.set_index("OA11CD", inplace=True)
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
            area_coord = areas_coordinates_df.loc[area_name][["X", "Y"]].values
            area = Area(
                self,
                area_name,
                n_residents_df.loc[area_name],
                n_households_df.loc[area_name],
                {
                    "age_freq": age_df.loc[area_name],
                    "sex_freq": sex_df.loc[area_name],
                    "household_freq": household_compostion_df.loc[area_name],
                },
                area_coord,
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
            school_dist.distribute_kids_to_primary_school()
            school_dist.distribute_kids_to_secondary_school()

            pbar.update(1)
        pbar.close()
