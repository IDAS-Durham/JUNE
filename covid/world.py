from covid.inputs import Inputs
from covid.groups import *
from covid.interaction import *
from covid.infection import Infection
from covid.logger import Logger
from covid.time import Timer

# from covid.interaction import Interaction
# from covid.interaction_selector import InteractionSelector
# from covid.time import DayIterator
import pandas as pd
import numpy as np
from tqdm.auto import tqdm  # for a fancy progress bar
import yaml
import os
from covid import time


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
        self.read_defaults()
        self.timer = Timer(self.config["time"])
        self.people = []
        self.total_people = 0
        print("Reading inputs...")
        self.inputs = Inputs(zone=self.config["world"]["zone"])
        print("Initializing areas...")
        self.msoareas = MSOAreas(self)
        msoareas_distributor = MSOAreaDistributor(self.msoareas)
        msoareas_distributor.read_msoareas_census()
        self.areas = Areas(self)
        areas_distributor = AreaDistributor(self.areas, self.inputs)
        areas_distributor.read_areas_census()
        print("Initializing people...")
        self.people = People(self)
        pbar = tqdm(total=len(self.areas.members))
        for area in self.areas.members:
            # get msoa flow data for this oa area
            wf_area_df = self.inputs.workflow_df.loc[(area.msoarea,)]
            person_distributor = PersonDistributor(
                self.people,
                area,
                self.msoareas,
                self.inputs.companysector_by_sex_df,
                wf_area_df,
            )
            person_distributor.populate_area()
            pbar.update(1)
        pbar.close()
        print("Initializing households...")
        pbar = tqdm(total=len(self.areas.members))
        self.households = Households(self)
        for area in self.areas.members:
            household_distributor = HouseholdDistributor(self, area)
            household_distributor.distribute_people_to_household()
            pbar.update(1)
        pbar.close()
        print("Initializing schools...")
        self.schools = Schools(self, self.areas, self.inputs.school_df)
        pbar = tqdm(total=len(self.areas.members))
        for area in self.areas.members:
            self.distributor = SchoolDistributor(self.schools, area)
            self.distributor.distribute_kids_to_school()
            pbar.update(1)
        pbar.close()
        self.interaction = self.initialize_interaction()
        # print("Initializing Companies...")
        # self.companies = Companies(self)
        # pbar = tqdm(total=len(self.msoareas.members))
        # for area in self.msoareas.members:
        #    self.distributor = CompanyDistributor(self.companies, area)
        #    self.distributor.distribute_adults_to_companies()
        #    pbar.update(1)
        # pbar.close()
        self.logger = Logger(self, self.config["logger"]["save_path"])
        print("Done.")

    @classmethod
    def from_pickle(cls, pickle_obj="/cosma7/data/dp004/dc-quer1/world.pkl"):
        """
        Initializes a world instance from an already populated world.
        """
        import pickle

        with open(pickle_obj, "rb") as f:
            world = pickle.load(f)
        return world

    @classmethod
    def from_config(cls, config_file):
        return cls(config_file)

    def read_defaults(self):
        default_config_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "..",
            "configs",
            "defaults",
            "world.yaml",
        )
        with open(default_config_path, "r") as f:
            default_config = yaml.load(f, Loader=yaml.FullLoader)
        for key in default_config.keys():
            if key not in self.config:
                self.config[key] = default_config[key]

    def initialize_interaction(self):
        interaction_type = self.config["interaction"]["type"]
        if "parameters" in self.config["interaction"]:
            interaction_parameters = self.config["interaction"]["parameters"]
        else:
            interaction_parameters = {}
        interaction_class_name = "Interaction" + interaction_type.capitalize()
        interaction = globals()[interaction_class_name](interaction_parameters, self)
        return interaction

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
                company_df[company_df["msoa11cd"] == "E02002559"][
                    [
                        "Micro (0 to 9)",
                        "10 to 19",
                        "20 to 49",
                        "50 to 99",
                        "100 to 249",
                        "250 to 499",
                        "500 to 999",
                        "1000+",
                    ]
                ].values,
            )
            areas_dict[i] = area
        return areas_dict

    def set_active_group_to_people(self, active_groups):
        for group_name in active_groups:
            group = getattr(self, group_name)
            group.set_active_members()

    def set_allpeople_free(self):
        for person in self.people.members:
            person.active_group = None

    def seed_infections_group(self, group, n_infections):
        #    print (n_infections,group.people)
        choices = np.random.choice(group.size(), n_infections)
        infecter_reference = Infection(None, self.timer, self.config)
        for choice in choices:
            infecter_reference.infect(group.people[choice])

    def do_timestep(self, day_iter):
        active_groups = self.timer.active_groups()
        if active_groups == None or len(active_groups) == 0:
            print("==== do_timestep(): no active groups found. ====")
            return
        # update people (where they are according to time)
        self.set_active_group_to_people(active_groups)
        # infect people in groups
        groups_instances = [getattr(self, group) for group in active_groups]
        self.interaction.groups = groups_instances
        self.interaction.time_step()
        self.set_allpeople_free()

    def group_dynamics(self):
        print(
            "Starting group_dynamics for ",
            self.timer.total_days,
            " days at day",
            self.timer.day,
        )
        assert sum(self.config["time"]["step_duration"]["weekday"].values()) == 24
        # TODO: move to function that checks the config file (types, values, etc...)
        # initialize the interaction class with an infection selector
        print("Infecting indivuals in their household.")
        for household in self.households.members:
            self.seed_infections_group(household, 1)
        print(
            "starting the loop ..., at ",
            self.timer.day,
            " days, to run for ",
            self.timer.total_days,
            " days",
        )
        while self.timer.day <= self.timer.total_days:
            self.do_timestep(self.timer)
            self.logger.log_timestep(self.timer.day)
            next(self.timer)


if __name__ == "__main__":
    world = World()
    # world = World.from_pickle()
    world.group_dynamics()
