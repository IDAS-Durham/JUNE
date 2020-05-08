import os
import pickle
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import numpy as np
import yaml
from tqdm.auto import tqdm  # for a fancy progress bar

from june.geography import Geography
from june.demography import Demography
from june.logger_creation import logger

logger = logging.getLogger(__name__)


class World:
    """
    This Class creates the world that will later be simulated.
    The world will be stored in pickle, but a better option needs to be found.
    
    Note: BoxMode = Demography +- Sociology - Geography
    """
    
    def __init__(
        self,
        #geography: "Geography",
        #demography: "Demography",
        #sociology: "Sociology",
        configs_dir: str = os.path.dirname(os.path.realpath(__file__))+"../configs/",
        output_dir: str = "./results/",
    ):
        self.configs_dir = configs_dir
        self.test_output_dir(output_dir)
        self.output_dir = output_dir
        
        # read configs
        #self.read_config(config_file)
        #self.read_defaults()


    def test_output_dir(self, output_dir: str):
        """ Create output directory if it doesn't exist yet """
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)


    def to_pickle(self, filename: str = None):
        """
        Write the world to file. Comes in handy when setting up the world
        takes a long time.
        """
        if filename is None:
            filename = os.path.join(self.output_dir, "world.log")
        with open(filename, "wb") as f:
            pickle.dump(self, f)
    
#    def geography():
#        self.initialize_areas()
#        self.initialize_super_areas()
#    
#    def humanity():
#        self.people = []
#        self.total_people = 0
#        self.initialize_people()
#    
#    def sociology():
#        self.relevant_groups = self.get_simulation_groups()
#        self.commute_generator = CommuteGenerator.from_file(
#            self.inputs.commute_generator_path
#        )
#        self.initialize_households()
#        self.initialize_hospitals()
#        self.initialize_cemeteries()
#        self.initialize_schools()
#        self.initialize_companies()
#        #self.initialize_boundary() #TODO
#        self.initialize_pubs()
#        #self.group_maker = GroupMaker(self)
#
#    def to_pickle(self, pickle_obj=os.path.join("..", "data", "world.pkl")):
#        """
#        Write the world to file. Comes in handy when setting up the world
#        takes a long time.
#        """
#        with open(pickle_obj, "wb") as f:
#            pickle.dump(self, f)
#
#    @classmethod
#    def from_config(cls, config_file):
#        return cls(config_file)
#
#    def read_config(self, config_file):
#        if config_file is None:
#            config_file = os.path.join(
#                os.path.dirname(os.path.realpath(__file__)),
#                "..",
#                "configs",
#                "config_example.yaml",
#            )
#        with open(config_file, "r") as f:
#            self.config = yaml.load(f, Loader=yaml.FullLoader)
#
#    def get_simulation_groups(self):
#        """
#        Reads all the different groups specified in the time section of the configuration file.
#        """
#        timesteps_config = self.config["time"]["step_active_groups"]
#        active_groups = []
#        for daytype in timesteps_config.keys():
#            for timestep in timesteps_config[daytype].values():
#                for group in timestep:
#                    active_groups.append(group)
#        active_groups = np.unique(active_groups)
#        return active_groups
#
#    def read_defaults(self):
#        """
#        Read config files for the world and it's active groups.
#        """
#        basepath = os.path.join(
#            os.path.dirname(os.path.realpath(__file__)),
#            "..",
#            "configs",
#            "defaults",
#        )
#        # global world settings
#        default_config_path = os.path.join(basepath, "world.yaml")
#        with open(default_config_path, "r") as f:
#            default_config = yaml.load(f, Loader=yaml.FullLoader)
#        for key in default_config.keys():
#            if key not in self.config:
#                self.config[key] = default_config[key]
#        # active group settings
#        for relevant_group in self.relevant_groups:
#            group_config_path = os.path.join(basepath, f"{relevant_group}.yaml")
#            if os.path.isfile(group_config_path):
#                with open(group_config_path, "r") as f:
#                    default_config = yaml.load(f, Loader=yaml.FullLoader)
#                for key in default_config.keys():
#                    if key not in self.config:
#                        self.config[key] = default_config[key]
#
#    def initialize_box_mode(self, region=None, n_people=None):
#        """
#        Sets the simulation to run in a single box, with everyone inside and no 
#        schools, households, etc.
#        Useful for testing interaction models and comparing to SIR.
#        """
#        print("Setting up box mode...")
#        self.boxes = Boxes()
#        box = BoxGenerator(self, region, n_people)
#        self.boxes.members = [box]
#        self.people = People(self)
#        self.people.members = box.people
#
#    def initialize_cemeteries(self):
#        self.cemeteries = Cemeteries(self)
#
#    def initialize_hospitals(self):
#        self.hospitals = Hospitals.from_file(
#            self.inputs.hospital_data_path,
#            self.inputs.hospital_config_path,
#            box_mode = self.box_mode
#        )
#
#        pbar = tqdm(total=len(self.super_areas.members))
#        for super_area in self.super_areas.members:
#            distributor = HospitalDistributor(self.hospitals, super_area)
#            pbar.update(1)
#        pbar.close()
#
#    def initialize_pubs(self):
#        print("Creating Pubs **********")
#        self.pubs = Pubs(self, self.inputs.pubs_df, self.box_mode)
#
#    def initialize_areas(self):
#        """
#        Each output area in the world is represented by an Area object.
#        This Area object contains the demographic information about
#        people living in it.
#        """
#        print("Initializing areas...")
#        self.areas = Areas.from_file(
#            self.inputs.n_residents_file,
#            self.inputs.age_freq_file,
#            self.inputs.sex_freq_file,
#            self.inputs.household_composition_freq_file,
#        )
#        areas_distributor = AreaDistributor(
#            self.areas,
#            self.inputs.area_mapping_df,
#            self.inputs.areas_coordinates_df,
#            self.relevant_groups,
#        )
#        areas_distributor.read_areas_census()
#
#    def initialize_super_areas(self):
#        """
#        An super_area is a group of areas. We use them to store company data.
#        """
#        print("Initializing SuperAreas...")
#        self.super_areas = SuperAreas(self)
#        super_areas_distributor = SuperAreaDistributor(
#            self.super_areas,
#            self.relevant_groups,
#        )
#
#    def initialize_people(self):
#        """
#        Populates the world with person instances.
#        """
#        print("Initializing people...")
#        #self.people = People.from_file(
#        #    self.inputs.,
#        #    self.inputs.,
#        #)
#        self.people = People(self)
#        pbar = tqdm(total=len(self.areas.members))
#        for area in self.areas.members:
#            # get msoa flow data for this oa area
#            wf_area_df = self.inputs.workflow_df.loc[(area.super_area.name,)]
#            person_distributor = PersonDistributor(
#                self,
#                self.timer,
#                self.people,
#                self.areas,
#                area,
#                self.super_areas,
#                self.inputs.compsec_by_sex_df,
#                wf_area_df,
#                self.inputs.key_compsec_ratio_by_sex_df,
#                self.inputs.key_compsec_distr_by_sex_df,
#            )
#            person_distributor.populate_area()
#            pbar.update(1)
#        pbar.close()
#
#    def initialize_households(self):
#        """
#        Calls the HouseholdDistributor to assign people to households following
#        the census household compositions.
#        """
#        print("Initializing households...")
#        pbar = tqdm(total=len(self.areas.members))
#        self.households = Households(self)
#        for area in self.areas.members:
#            household_distributor = HouseholdDistributor(
#                self.households,
#                area,
#                self.areas,
#                self.config,
#            )
#            household_distributor.distribute_people_to_household()
#            pbar.update(1)
#        pbar.close()
#
#    def initialize_schools(self):
#        """
#        Schools are organized in NN k-d trees by age group, so we can quickly query
#        the closest age compatible school to a certain kid.
#        """
#        print("Initializing schools...")
#        self.schools = Schools.from_file(
#            self.inputs.school_data_path,
#            self.inputs.school_config_path
#        )
#        pbar = tqdm(total=len(self.areas.members))
#        for area in self.areas.members:
#           self.distributor = SchoolDistributor.from_file(
#                self.schools,
#                area,
#                self.inputs.school_config_path,
#            )
#           self.distributor.distribute_kids_to_school()
#           self.distributor.distribute_teachers_to_school()
#           pbar.update(1)
#        pbar.close()
#
#    def initialize_companies(self):
#        """
#        Companies live in super_areas.
#        """
#        print("Initializing Companies...")
#        self.companies = Companies.from_file(
#            self.inputs.companysize_file,
#            self.inputs.company_per_sector_per_msoa_file,
#        )
#        pbar = tqdm(total=len(self.super_areas.members))
#        for super_area in self.super_areas.members:
#            self.distributor = CompanyDistributor(
#                self.companies,
#                super_area,
#                self.config, 
#            )
#            self.distributor.distribute_adults_to_companies()
#            pbar.update(1)
#        pbar.close()
#
#    def initialize_boundary(self):
#        """
#        Create a population that lives in the boundary.
#        It interacts with the population in the simulated region only
#        in companies. No interaction takes place during leasure activities.
#        """
#        print("Creating Boundary...")
#        self.boundary = Boundary(self)
#
#
#    def set_allpeople_free(self):
#        for person in self.people.members:
#            person.active_group = None


if __name__ == "__main__":
    world = World(
    )
