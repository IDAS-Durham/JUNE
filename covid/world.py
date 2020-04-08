from sklearn.neighbors import BallTree
from covid.inputs import Inputs
from covid.area import Area
from covid.distributors import *
from covid.school import School, SchoolError
import pandas as pd
import numpy as np
from tqdm.auto import tqdm  # for a fancy progress bar
import yaml
import os


class World:
    """
    Stores global information about the simulation
    """

    def __init__(self, config_file=None):
        print("Initializing world...")
        if config_file is None:
            config_file = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "..",
                "configs",
                "config_example.yaml",
            )
        with open(config_file, "r") as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)
        self.inputs = Inputs(zone=self.config["world"]["zone"])
        self.people = {}
        self.total_people = 0
        self.decoder_sex = {}
        self.decoder_age = {}
        self.encoder_household_composition = {}
        self.decoder_household_composition = {}
        self.areas = self.read_areas_census(self.inputs.household_dict)
        #self.msoareas = self.read_msoareas_census(self.inputs.company_df)
        print("Creating schools...")
        self._init_schools(self.inputs.school_df)
        # self.secondary_school_tree = self.create_school_tree(inputs.secondary_school)
        #self._init_companies(self.inputs.company_df)
        print("Done.")

    def _compute_age_group_mean(self, agegroup):
        try:
            age_1, age_2 = agegroup.split("-")
            if age_2 == "XXX":
                agemean = 90
            else:
                age_1 = float(age_1)
                age_2 = float(age_2)
                agemean = (age_2 + age_1) / 2.0
        except:
            agemean = int(agegroup)
        return agemean

    def _init_schools(self, school_df):
        """
        Initializes schools.
        """
        SCHOOL_AGE_THRESHOLD = [1, 7]
        schools = {}
        school_age = list(self.decoder_age.values())[
            SCHOOL_AGE_THRESHOLD[0] : SCHOOL_AGE_THRESHOLD[1]
        ]
        school_trees = {}
        school_agegroup_to_global_indices = (
            {}
        )  # stores for each age group the index to the school
        # create school neighbour trees
        for agegroup in school_age:
            school_agegroup_to_global_indices[
                agegroup
            ] = {}  # this will be used to track school universally
            mean = self._compute_age_group_mean(agegroup)
            _school_df_agegroup = school_df[
                (school_df["age_min"] <= mean) & (school_df["age_max"] >= mean)
            ]
            school_trees[agegroup] = self._create_school_tree(_school_df_agegroup)
        # create schools and put them in the right age group
        for i, (index, row) in enumerate(school_df.iterrows()):
            school = School(
                i,
                np.array(row[["latitude", "longitude"]].values, dtype=np.float64),
                row["NOR"],
                row["age_min"],
                row["age_max"],
            )
            # to which age group does this school belong to?
            for agegroup in school_age:
                agemean = self._compute_age_group_mean(agegroup)
                if school.age_min <= agemean and school.age_max >= agemean:
                    school_agegroup_to_global_indices[agegroup][
                        len(school_agegroup_to_global_indices[agegroup])
                    ] = i
            schools[i] = school
        # store variables to class
        self.schools = schools
        self.school_trees = school_trees
        self.school_agegroup_to_global_indices = school_agegroup_to_global_indices
        return None

    def get_closest_schools(self, age, area, k):
        """
        Returns the k schools closest to the output area centroid.
        """
        # distances, neighbours = self.schools_tree.query(
        #    np.deg2rad(area.coordinates.reshape(1, -1)), r=radius, sort_results=True,
        # )
        school_tree = self.school_trees[age]
        distances, neighbours = school_tree.query(
            np.deg2rad(area.coordinates.reshape(1, -1)), k=k, sort_results=True,
        )
        return neighbours[0]

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
        This is all on the OA layer.
        """
        # TODO: put this in input class
        areas_coordinates_df = pd.read_csv(
            "../data/geographical_data/oa_coorindates.csv"
        )
        areas_coordinates_df.set_index("OA11CD", inplace=True)
        n_residents_df = input_dict.pop("n_residents")
        # n_households_df = input_dict.pop("n_households")
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
            area_coord = areas_coordinates_df.loc[area_name][["Y", "X"]].values
            area = Area(
                self,
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
        return areas_dict

    def read_msoareas_census(self, company_df):
        """
        Creat link between OA and MSOA layers.
        """
        dirs = "../data/census_data/area_code_translations/"
        area_trans_df = pd.read_csv(
            dirs + "./PCD11_OA11_LSOA11_MSOA11_LAD11_RGN17_FID_EW_LU.csv"
        )
        area_trans_df = area_trans_df.drop_duplicates(subset="OA11CD").set_index(
            "OA11CD"
        )["MSOA11CD"]

        areas_dict = {}
        for i, area_code in enumerate(company_df["MSOA11CD"].values):
            area = MSOAres(
                self,
                area_code,
                area_trans_df[area_trans_df["MSOA11CD"] == area_code].index.values,
                company_df[company_df["msoa11cd"] == "E02002559"][[
                    "Micro (0 to 9)", "10 to 19", "20 to 49", "50 to 99",
                    "100 to 249", "250 to 499", "500 to 999", "1000+",
                ]].values
            )
            areas_dict[i] = area
        return areas_dict

    def _init_companies(self, company_df):
        """
        Initializes companies.

        Input:
            company_df: pd.DataFrame
                Contains information on nr. of companies with nr. of employees per MSOA
        """
        LABOUR_AGE_THRESHOLD = [8, 13]
        companies = {}
        school_age = list(self.decoder_age.values())[
            SCHOOL_AGE_THRESHOLD[0] : SCHOOL_AGE_THRESHOLD[1]
        ]
        school_trees = {}
        school_agegroup_to_global_indices = (
            {}
        )  # stores for each age group the index to the school
        # create school neighbour trees
        for agegroup in school_age:
            school_agegroup_to_global_indices[
                agegroup
            ] = {}  # this will be used to track school universally
            mean = self._compute_age_group_mean(agegroup)
            _school_df_agegroup = school_df[
                (school_df["age_min"] <= mean) & (school_df["age_max"] >= mean)
            ]
            school_trees[agegroup] = self._create_school_tree(_school_df_agegroup)
        # create schools and put them in the right age group
        for i, (index, row) in enumerate(school_df.iterrows()):
            school = School(
                i,
                np.array(row[["latitude", "longitude"]].values, dtype=np.float64),
                row["NOR"],
                row["age_min"],
                row["age_max"],
            )
            # to which age group does this school belong to?
            for agegroup in school_age:
                agemean = self._compute_age_group_mean(agegroup)
                if school.age_min <= agemean and school.age_max >= agemean:
                    school_agegroup_to_global_indices[agegroup][
                        len(school_agegroup_to_global_indices[agegroup])
                    ] = i
            schools[i] = school
        # store variables to class
        self.schools = schools
        self.school_trees = school_trees
        self.school_agegroup_to_global_indices = school_agegroup_to_global_indices
        return None

    def populate_world(self):
        """
        Populates world with people, houses, schools, etc.
        """
        print("Populating world ...")
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

            # TODO: distribute workers to companies
            # work_dist = WorkDistributor(area)
            # work_dist.distribute_adults_to_work()

            pbar.update(1)

        #print("and make it work ...")
        #pbar = tqdm(total=len(self.msoareas.keys()))  # progress bar
        #for msoarea in self.msoareas.values():
            # TODO: distribute workers to companies
            # work_dist = WorkDistributor(msoarea)
            # work_dist.distribute_adults_to_companies()

            #pbar.update(1)

        pbar.close()


if __name__ == "__main__":

    world = World()
