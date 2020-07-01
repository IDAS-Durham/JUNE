import numpy as np
import matplotlib.pyplot as plt 
import pandas as pd
import time
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import sys

from june.demography.geography import Geography
from june.demography.demography import load_age_and_sex_generators_for_bins, Demography, Population
from june.paths import data_path
from june.seed import Seed
from june.infection.infection import InfectionSelector
from june.interaction import ContactAveraging
from june.groups import Hospital, Hospitals
from june.distributors import HospitalDistributor
from june.world import generate_world_from_hdf5
from june.groups import Cemeteries
from june.policy import Policy, Policies
from june.logger.read_logger import ReadLogger

from camps.paths import camp_data_path
from camps.world import World
from camps.groups.leisure import generate_leisure_for_world, generate_leisure_for_config
from camp_creation import generate_empty_world, populate_world, distribute_people_to_households # this is loaded from the ../camp_scripts folder
from camps.simulator import CampSimulator

from camps.groups import PumpLatrines, PumpLatrineDistributor
from camps.groups import DistributionCenters, DistributionCenterDistributor
from camps.groups import Communals, CommunalDistributor
from camps.groups import FemaleCommunals, FemaleCommunalDistributor
from camps.groups import Religiouss, ReligiousDistributor
from camps.groups import Shelter, Shelters, ShelterDistributor
from june.groups.leisure import HouseholdVisitsDistributor

# create empty world's geography
world = generate_empty_world()

# populate empty world
populate_world(world)

# distribute people to households
distribute_people_to_households(world)

# this is not working
hospitals= Hospitals.from_file(
    filename=camp_data_path / 'input/hospitals/hospitals.csv'
)
world.hospitals = hospitals
hospital_distributor = HospitalDistributor(hospitals, 
                                           medic_min_age=20,
                                           patients_per_medic=10)

hospital_distributor.distribute_medics_from_world(world.people)

world.pump_latrines = PumpLatrines.for_areas(world.areas)
world.distribution_centers = DistributionCenters.for_areas(world.areas)
world.communals = Communals.for_areas(world.areas)
world.female_communals = FemaleCommunals.for_areas(world.areas)
world.religiouss = Religiouss.for_areas(world.areas)

#world.box_mode = False
world.cemeteries = Cemeteries()

world.shelters = Shelters.for_areas(world.areas)
shelter_distributor = ShelterDistributor(sharing_shelter_ratio = 0.75) # proportion of families that share a shelter
for area in world.areas:
    shelter_distributor.distribute_people_in_shelters(area.shelters, area.households)

selector = InfectionSelector.from_file()

interaction = ContactAveraging.from_file(config_filename='../configs_camps/defaults/interaction/ContactInteraction.yaml',\
                                         selector=selector)

social_distance = Policy(policy="social_distance",
                         start_time=datetime(2021, 3, 25), 
                         end_time=datetime(2021, 4, 1))
policies = Policies.from_file([social_distance])

seed = Seed(world.super_areas,
           selector)

seed.unleash_virus(n_cases=5)

CONFIG_PATH = "../configs_camps/config_example.yaml"

leisure_instance = generate_leisure_for_config(
            world=world, config_filename=CONFIG_PATH
)
leisure_instance.leisure_distributors = [
    PumpLatrineDistributor.from_config(pump_latrines=world.pump_latrines),
    DistributionCenterDistributor.from_config(distribution_centers=world.distribution_centers),
    CommunalDistributor.from_config(communals=world.communals),
    FemaleCommunalDistributor.from_config(female_communals=world.female_communals),
]

simulator = CampSimulator.from_file(
     world, interaction, selector,
    leisure = leisure_instance,
    policies=policies,
    config_filename = CONFIG_PATH,
    #seed=seed
)

leisure_instance.leisure_distributors

simulator.timer.reset()

simulator.run()
