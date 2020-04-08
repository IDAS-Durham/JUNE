from covid.inputs import Inputs
from covid.groups import *
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
        # decoders for census variables 
        self.decoder_age = {}
        self.decoder_sex = {}
        self.decoder_household_composition = {}
        self.encoder_household_composition = {}
        print("Reading inputs...")
        self.inputs = Inputs(zone=self.config["world"]["zone"])
        print("Initializing areas...")
        self.areas = Areas(self)
        areas_distributor = AreaDistributor(self.areas, self.inputs.household_dict)
        areas_distributor.read_areas_census()
        print("Initializing people...")
        self.people = People(self)
        for area in self.areas.members.values():
            person_distributor = PersonDistributor(self.people, area)
            person_distributor.populate_area()
        print("Initializing households...")
        for area in self.areas.members.values():
            area.households = Households(area)
            household_distributor = HouseholdDistributor(self, area.households, area)
            household_distributor.distribute_people_to_household()
        print("Initializing schools...")
        self.schools = Schools(self, self.areas, self.inputs.school_df)
        for area in self.areas.members.values():
            self.distributor = SchoolDistributor(self.schools, area)
            self.distributor.distribute_kids_to_school()
        '''
        #self.msoareas = self.read_msoareas_census(self.inputs.company_df)
        print("Creating schools...")
        self._init_schools(self.inputs.school_df)
        #self._init_companies(self.inputs.company_df)
        print("Done.")
        '''

    @classmethod
    def from_pickle(cls, pickle_obj="/cosma7/data/dp004/dc-quer1/world.pkl"):
        """
        Initializes a world instance from an already populated world.
        """
        import pickle
        with open(pickle_obj, "r") as f:
            world = pickle.load(f)
        return world
    
    @classmethod
    def from_config(cls, config_file):
        return cls(config_file)

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

    #def populate_world(self):
    #    """
    #    Populates world with people, houses, schools, etc.
    #    """
    #    print("Populating world ...")
    #    pbar = tqdm(total=len(self.areas.keys()))  # progress bar
    #    for area in self.areas.values():
    #        # create population
    #        people_dist = PeopleDistributor(area)
    #        people_dist.populate_area()

    #        # distribute people to households
    #        household_dist = HouseholdDistributor(area)
    #        household_dist.distribute_people_to_household()

    #        # distribute kids to schools
    #        school_dist = SchoolDistributor(area)
    #        school_dist.distribute_kids_to_school()

    #        # TODO: distribute workers to companies
    #        # work_dist = WorkDistributor(area)
    #        # work_dist.distribute_adults_to_work()

    #        pbar.update(1)

    #    #print("and make it work ...")
    #    #pbar = tqdm(total=len(self.msoareas.keys()))  # progress bar
    #    #for msoarea in self.msoareas.values():
    #        # TODO: distribute workers to companies
    #        # work_dist = WorkDistributor(msoarea)
    #        # work_dist.distribute_adults_to_companies()

    #        #pbar.update(1)

    #    pbar.close()

    def _active_groups(self, time):

        return self.config["world"]["step_active_groups"][time]

    def _set_active_members(self, active_groups):
        for group in active_groups:
            group._set_active_members()
    def _unset_active_members(self, active_groups):
        for group in active_groups:
            group._unset_active_members()


    def _infect(self, group, duration):
        for ind_group in world:
            break
            # check there are suceptible (if all infected don't run)
            # Call Frank

    def seed_infection(self, n_infected):
        pass

    def group_dynamics(self, total_days):

        time_steps = self.config["world"]["step_duration"].keys()
        assert sum(self.config["world"]["step_duration"].values()) == 24 
        # TODO: move to function that checks the config file (types, values, etc...)
        self.days = 0
        while self.days <= total_days:
            for time in time_steps:
                active_groups = self._active_groups(time)
                # update people (where they are according to time)
                self._set_active_members(active_groups)

                # infect people in groups
                for group in active_groups:
                    break
                        #self._infect(group,
#                                self.config["world"]["step_duration"]) # Call infection with how long it lasts
                self._unset_active_members(active_groups)
            self.days += 1

        

if __name__ == "__main__":

    world = World.from_pickle()
    world.group_dynamics(2)
