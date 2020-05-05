import os
import pickle
import logging
import logging.config

import numpy as np
import yaml
from tqdm.auto import tqdm  # for a fancy progress bar

from covid.box_generator import BoxGenerator
from covid.commute import CommuteGenerator
from covid.groups import *
from covid.inputs import Inputs
from covid.logger import Logger
from covid.time import Timer
from covid.infection import transmission
from covid import interaction
from covid.infection import symptoms
from covid.infection import Infection
from covid.groups.people import HealthIndex


class World:
    """
    Stores global information about the simulation
    """

    def __init__(
        self, config_file=None, box_mode=False, box_n_people=None, box_region=None
    ):
        print("Initializing world...")
        # read configs
        self.read_config(config_file)
        self.relevant_groups = self.get_simulation_groups()
        self.read_defaults()
        # set up logging
        self.world_creation_logger(self.config["logger"]["save_path"])
        # start initialization
        self.box_mode = box_mode
        self.timer = Timer(self.config["time"])
        self.people = []
        self.total_people = 0
        print("Reading inputs...")
        self.inputs = Inputs(zone=self.config["world"]["zone"])
        if self.box_mode:
            self.initialize_hospitals()
            self.initialize_cemeteries()
            self.initialize_box_mode(box_region, box_n_people)
        else:
            print("Initializing commute generator...")
            self.commute_generator = CommuteGenerator.from_file(
                self.inputs.commute_generator_path
            )
            self.initialize_areas()
            self.initialize_msoa_areas()
            self.initialize_people()
            self.initialize_households()
            self.initialize_hospitals()
            self.initialize_cemeteries()
            if "schools" in self.relevant_groups:
                self.initialize_schools()
            else:
                print("schools not needed, skipping...")
            if "companies" in self.relevant_groups:
                self.initialize_companies()
            else:
                print("companies not needed, skipping...")
            if "boundary" in self.relevant_groups:
                self.initialize_boundary()
            else:
                print("nothing exists outside the simulated region")
            if "pubs" in self.relevant_groups:
                self.initialize_pubs()
                self.group_maker = GroupMaker(self)
            else:
                print("pubs not needed, skipping...")
        self.interaction = self.initialize_interaction()
        self.logger = Logger(
            self, self.config["logger"]["save_path"], box_mode=box_mode
        )
        print("Done.")

    def world_creation_logger(
        self, save_path, config_file=None, default_level=logging.INFO,
    ):
        """
        """
        # where to read and write files
        if config_file is None:
            config_file = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "..",
                "configs",
                "config_world_creation_logger.yaml",
            )
        # creating logger
        log_file = os.path.join(save_path, "world_creation.log")
        if os.path.isfile(config_file):
            with open(config_file, "rt") as f:
                log_config = yaml.safe_load(f.read())
            logging.config.dictConfig(log_config)
        else:
            logging.basicConfig(filename=log_file, level=logging.INFO)

    def to_pickle(self, pickle_obj=os.path.join("..", "data", "world.pkl")):
        """
        Write the world to file. Comes in handy when setting up the world
        takes a long time.
        """
        with open(pickle_obj, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def from_pickle(cls, pickle_obj="/cosma7/data/dp004/dc-quer1/world.pkl"):
        """
        Initializes a world instance from an already populated world.
        """
        with open(pickle_obj, "rb") as f:
            world = pickle.load(f)
        return world

    @classmethod
    def from_config(cls, config_file):
        return cls(config_file)

    def read_config(self, config_file):
        if config_file is None:
            config_file = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "..",
                "configs",
                "config_example.yaml",
            )
        with open(config_file, "r") as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)

    def get_simulation_groups(self):
        """
        Reads all the different groups specified in the time section of the configuration file.
        """
        timesteps_config = self.config["time"]["step_active_groups"]
        active_groups = []
        for daytype in timesteps_config.keys():
            for timestep in timesteps_config[daytype].values():
                for group in timestep:
                    active_groups.append(group)
        active_groups = np.unique(active_groups)
        return active_groups

    def read_defaults(self):
        """
        Read config files for the world and it's active groups.
        """
        basepath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "..", "configs", "defaults",
        )
        # global world settings
        default_config_path = os.path.join(basepath, "world.yaml")
        with open(default_config_path, "r") as f:
            default_config = yaml.load(f, Loader=yaml.FullLoader)
        for key in default_config.keys():
            if key not in self.config:
                self.config[key] = default_config[key]
        # active group settings
        for relevant_group in self.relevant_groups:
            group_config_path = os.path.join(basepath, f"{relevant_group}.yaml")
            if os.path.isfile(group_config_path):
                with open(group_config_path, "r") as f:
                    default_config = yaml.load(f, Loader=yaml.FullLoader)
                for key in default_config.keys():
                    if key not in self.config:
                        self.config[key] = default_config[key]

    def initialize_box_mode(self, region=None, n_people=None):
        """
        Sets the simulation to run in a single box, with everyone inside and no 
        schools, households, etc.
        Useful for testing interaction models and comparing to SIR.
        """
        print("Setting up box mode...")
        self.boxes = Boxes()
        box = BoxGenerator(self, region, n_people)
        self.boxes.members = [box]
        self.people = People(self)
        self.people.members = box.people

    def initialize_cemeteries(self):
        self.cemeteries = Cemeteries(self)

    def initialize_hospitals(self):
        self.hospitals = Hospitals.from_file(
            self.inputs.hospital_data_path,
            self.inputs.hospital_config_path,
            box_mode=self.box_mode,
        )

        pbar = tqdm(total=len(self.msoareas.members))
        for msoarea in self.msoareas.members:
            distributor = HospitalDistributor(self.hospitals, msoarea)
            pbar.update(1)
        pbar.close()

    def initialize_pubs(self):
        print("Creating Pubs **********")
        self.pubs = Pubs(self, self.inputs.pubs_df, self.box_mode)

    def initialize_areas(self):
        """
        Each output area in the world is represented by an Area object. This Area object contains the
        demographic information about people living in it.
        """
        print("Initializing areas...")
        self.areas = OAreas(self)
        areas_distributor = OAreaDistributor(self.areas, self.inputs)
        areas_distributor.read_areas_census()

    def initialize_msoa_areas(self):
        """
        An MSOA area is a group of output areas. We use them to store company data.
        """
        print("Initializing MSOAreas...")
        self.msoareas = MSOAreas(self)
        msoareas_distributor = MSOAreaDistributor(self.msoareas)

    def initialize_people(self):
        """
        Populates the world with person instances.
        """
        print("Initializing people...")
        # self.people = People.from_file(
        #    self.inputs.,
        #    self.inputs.,
        # )
        self.people = People(self)
        pbar = tqdm(total=len(self.areas.members))
        for area in self.areas.members:
            # get msoa flow data for this oa area
            wf_area_df = self.inputs.workflow_df.loc[(area.msoarea.name,)]
            person_distributor = PersonDistributor(
                self.timer,
                self.people,
                area,
                self.msoareas,
                self.inputs.compsec_by_sex_df,
                wf_area_df,
                self.inputs.key_compsec_ratio_by_sex_df,
                self.inputs.key_compsec_distr_by_sex_df,
            )
            person_distributor.populate_area()
            pbar.update(1)
        pbar.close()

    def initialize_households(self):
        """
        Calls the HouseholdDistributor to assign people to households following
        the census household compositions.
        """
        print("Initializing households...")
        pbar = tqdm(total=len(self.areas.members))
        self.households = Households(self)
        for area in self.areas.members:
            household_distributor = HouseholdDistributor(self, area)
            household_distributor.distribute_people_to_household()
            pbar.update(1)
        pbar.close()

    def initialize_schools(self):
        """
        Schools are organized in NN k-d trees by age group, so we can quickly query
        the closest age compatible school to a certain kid.
        """
        print("Initializing schools...")
        self.schools = Schools.from_file(
            self.inputs.school_data_path, self.inputs.school_config_path
        )
        pbar = tqdm(total=len(self.areas.members))
        for area in self.areas.members:
            self.distributor = SchoolDistributor.from_file(
                self.schools, area, self.inputs.school_config_path
            )
            self.distributor.distribute_kids_to_school()
            self.distributor.distribute_teachers_to_school()
            pbar.update(1)
        pbar.close()

    def initialize_companies(self):
        """
        Companies live in MSOA areas.
        """
        print("Initializing Companies...")
        self.companies = Companies.from_file(
            self.inputs.companysize_file, self.inputs.company_per_sector_per_msoa_file,
        )
        pbar = tqdm(total=len(self.msoareas.members))
        for msoarea in self.msoareas.members:
            self.distributor = CompanyDistributor(self.companies, msoarea)
            self.distributor.distribute_adults_to_companies()
            pbar.update(1)
        pbar.close()

    def initialize_boundary(self):
        """
        Create a population that lives in the boundary.
        It interacts with the population in the simulated region only
        in companies. No interaction takes place during leasure activities.
        """
        print("Creating Boundary...")
        self.boundary = Boundary(self)

    def initialize_interaction(self):
        interaction_type = self.config["interaction"]["type"]
        interaction_class_name = "Interaction" + interaction_type.capitalize()
        interaction_instance = getattr(interaction, interaction_class_name).from_file()
        return interaction_instance

    def set_active_group_to_people(self, active_groups):
        for group_name in active_groups:
            grouptype = getattr(self, group_name)
            if "pubs" in active_groups:
                self.group_maker.distribute_people(group_name)
            for group in grouptype.members:
                group.set_active_members()

    def set_allpeople_free(self):
        for person in self.people.members:
            person.active_group = None

    def initialize_infection(self):
        if "parameters" in self.config["infection"]:
            infection_parameters = self.config["infection"]["parameters"]
        else:
            infection_parameters = {}
        if "transmission" in self.config["infection"]:
            transmission_type = self.config["infection"]["transmission"]["type"]
            transmission_parameters = self.config["infection"]["transmission"][
                "parameters"
            ]
            transmission_class_name = "Transmission" + transmission_type.capitalize()
        else:
            trans_class = "TransmissionConstant"
            transmission_parameters = {}
        trans_class = getattr(transmission, transmission_class_name)
        transmission_class = trans_class(**transmission_parameters)
        if "symptoms" in self.config["infection"]:
            symptoms_type = self.config["infection"]["symptoms"]["type"]
            symptoms_parameters = self.config["infection"]["symptoms"]["parameters"]
            symptoms_class_name = "Symptoms" + symptoms_type.capitalize()
        else:
            symptoms_class_name = "SymptomsGaussian"
            symptoms_parameters = {}
        symp_class = getattr(symptoms, symptoms_class_name)
        reference_health_index = HealthIndex().get_index_for_age(40)
        symptoms_class = symp_class(
            health_index=reference_health_index, **symptoms_parameters
        )
        infection = Infection(
            self.timer.now, transmission_class, symptoms_class, **infection_parameters
        )
        return infection

    def seed_infections_group(self, group, n_infections):
        choices = np.random.choice(group.size, n_infections)
        infecter_reference = self.initialize_infection()
        for choice in choices:
            infecter_reference.infect_person_at_time(
                group.people[choice], self.timer.now
            )
        group.update_status_lists(self.timer.now, delta_time=0)

    def seed_infections_box(self, n_infections):
        print("seed ", n_infections, "infections in box")
        choices = np.random.choice(self.people.members, n_infections, replace=False)
        infecter_reference = self.initialize_infection()
        for choice in choices:
            infecter_reference.infect_person_at_time(choice, self.timer.now)
        self.boxes.members[0].update_status_lists(self.timer.now, delta_time=0)

    def do_timestep(self):
        active_groups = self.timer.active_groups()
        # print ("=====================================================")
        # print ("=== active groups: ",active_groups,".")
        if active_groups == None or len(active_groups) == 0:
            print("==== do_timestep(): no active groups found. ====")
            return
        # update people (where they are according to time)
        self.set_active_group_to_people(active_groups)
        # infect people in groups
        group_instances = [getattr(self, group) for group in active_groups]
        for group_type in group_instances:
            for group in group_type.members:
                self.interaction.time_step(self.timer.now, self.timer.duration, group)
        # Update people that recovered in hospitals
        for hospital in self.hospitals.members:
            hospital.update_status_lists(self.timer.now, delta_time=0)
        self.set_allpeople_free()

    def group_dynamics(self, n_seed=100):
        print(
            "Starting group_dynamics for ",
            self.timer.total_days,
            " days at day",
            self.timer.day,
        )
        assert sum(self.config["time"]["step_duration"]["weekday"].values()) == 24
        # TODO: move to function that checks the config file (types, values, etc...)
        # initialize the interaction class with an infection selector
        if self.box_mode:
            self.seed_infections_box(n_seed)
        else:
            print(
                "Infecting individuals in their household,",
                "for in total ",
                len(self.households.members),
                " households.",
            )
            for household in self.households.members:
                self.seed_infections_group(household, 1)
        print(
            "starting the loop ..., at ",
            self.timer.day,
            " days, to run for ",
            self.timer.total_days,
            " days",
        )

        for day in self.timer:
            if day > self.timer.total_days:
                break
            self.logger.log_timestep(day)
            self.do_timestep()


if __name__ == "__main__":
    world = World(config_file=os.path.join("../configs", "config_example.yaml"))

    # world = World(config_file=os.path.join("../configs", "config_boxmode_example.yaml"),
    #              box_mode=True,box_n_people=100)

    # world = World.from_pickle()
    # world.group_dynamics()
