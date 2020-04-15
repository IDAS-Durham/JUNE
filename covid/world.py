from covid.inputs import Inputs
import covid.groups
from covid.logger import Logger
from covid.infection_selector import InfectionSelector
from covid.interaction import Interaction, CollectiveInteraction
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
            indx = np.where(
                self.inputs.workflow_dict["home_msoa"] == area.msoarea
            )[0][0]
            workflow_dict = {
                "female_work_msoa": self.inputs.workflow_dict["female_work_msoa"][indx],
                "female_work_dist": self.inputs.workflow_dict["female_work_dist"][indx],
                "male_work_msoa": self.inputs.workflow_dict["male_work_msoa"][indx],
                "male_work_dist": self.inputs.workflow_dict["male_work_dist"][indx],
            }
            person_distributor = PersonDistributor(
                self.people,
                area,
                self.msoareas,
                self.inputs.companysector_by_sex_df,
                workflow_dict,
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
        self.msoareas = self.read_msoareas_census(self.inputs.company_df)
        print("Initializing Companies...")
        self.companies = Companies(self)
        for area in self.msoareas.members:
            self.distributor = CompanyDistributor(self.companies, area)
            self.distributor.distribute_adults_to_companies()
            pbar.update(1)
        pbar.close()
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

    def _active_groups(self, time):
        # households are always active
        always_active = ["households"]
        active = self.config["world"]["step_active_groups"][time]
        return active + always_active #always_active + active

    def set_active_group_to_people(self, active_groups):
        for group_name in active_groups:
            group = getattr(self, group_name)
            group.set_active_members()

    def set_allpeople_free(self):
        for person in self.people.members:
            person.active_group = None

    def _initialize_infection_selector_and_interaction(self, config):
        self.selector = InfectionSelector(config)
        self.interaction = CollectiveInteraction(self.selector)

    def seed_infections_group(self, group, n_infections, selector):
        choices = np.random.choice(group.size(), n_infections)
        for choice in choices:
            group.people[choice].set_infection(
                self.selector.make_infection(group.people[choice], self.time)
            )

    def do_timestep(self, timetag, duration):
        active_groups = self._active_groups(timetag)
        if active_groups == None or len(active_groups) == 0:
            print("==== do_timestep(): no active groups found. ====")
            return
        # update people (where they are according to time)
        self.set_active_group_to_people(active_groups)
        # infect people in groups
        groups_instances = [getattr(self, group) for group in active_groups]
        self.interaction.set_groups(groups_instances)
        self.interaction.set_time(self.time + duration)
        self.interaction.time_step()
        self.set_allpeople_free()

    def group_dynamics(self, total_days):
        self.days = 1
        self.time = 1.*self.days
        print("Starting group_dynamics for ", total_days, " days at day",self.days)
        time_steps = self.config["time"]["step_duration"]["weekday"].keys()
        assert sum(self.config["time"]["step_duration"]["weekday"].values()) == 24
        # TODO: move to function that checks the config file (types, values, etc...)
        # initialize the interaction class with an infection selector
        self._initialize_infection_selector_and_interaction(self.config)
        print ("Infecting indivuals in their household.")
        self.interaction.set_time(self.days)
        for household in self.households.members:
            self.seed_infections_group(household, self.days, self.selector)
        print ("starting the loop ..., at ",self.days," days, to run for ",total_days," days")
        while self.days <= total_days:
            for shift, timetag in enumerate(time_steps):
                duration = self.config["time"]["step_duration"]["weekday"][timetag]
                print("next step, time = ", self.time,"(tag = ",timetag,"), duration = ",(duration/24.))
                self.do_timestep(timetag, duration/24.)
                self.logger.log_timestep(self.days, shift)
                self.time += duration/24.
            self.days += 1


if __name__ == "__main__":
    world = World()
    # world = World.from_pickle()
    world.group_dynamics(2)
