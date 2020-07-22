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
from june.infection import Infection, HealthIndexGenerator
from june.infection_seed import InfectionSeed
from june.infection.infection import InfectionSelector
from june.interaction import ContactAveraging
from june.groups import Hospital, Hospitals
from june.distributors import HospitalDistributor
from june.world import generate_world_from_hdf5
from june.groups import Cemeteries
from june.policy import Policy, Policies
from june.logger.read_logger import ReadLogger

from camps.paths import camp_data_path, camp_configs_path
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

print('Total people = ', len(world.people))
print('Mean age = ', np.mean([person.age for person in world.people]))
#world.box_mode = False
world.cemeteries = Cemeteries()

world.shelters = Shelters.for_areas(world.areas)
shelter_distributor = ShelterDistributor(sharing_shelter_ratio = 0.75) # proportion of families that share a shelter
for area in world.areas:
    shelter_distributor.distribute_people_in_shelters(area.shelters, area.households)

health_index_generator = HealthIndexGenerator.from_file(asymptomatic_ratio=0.2)
selector = InfectionSelector.from_file(health_index_generator=health_index_generator)

interaction = ContactAveraging.from_file(config_filename=camp_configs_path / 'defaults/interaction/ContactInteraction_low.yaml',selector=selector)

policies = Policies.from_file(camp_configs_path / 'defaults/policy/policy.yaml') # no policies for now

cases_detected =  {
        'CXB-202': 3, 
        'CXB-204': 6, 
        'CXB-208': 8, 
        'CXB-203': 1,
        'CXB-207':2, 
        'CXB-213': 2,
        } # By the 24th May

print('Detected cases = ', sum(cases_detected.values()))

msoa_region_filename = camp_data_path / 'input/geography/area_super_area_region.csv'
msoa_region = pd.read_csv(msoa_region_filename)[["super_area", "region"]]
infection_seed = InfectionSeed(
        super_areas=world.super_areas,
        selector=selector,
        msoa_region = msoa_region
        )

for key, n_cases in cases_detected.items():
    infection_seed.unleash_virus_regional_cases(key, n_cases*10)
# Add some extra random cases
infection_seed.unleash_virus(n_cases=100)

print('Infected people in seed = ' , len(world.people.infected))

CONFIG_PATH = camp_configs_path / "config_example.yaml"

leisure_instance = generate_leisure_for_config(
            world=world, config_filename=CONFIG_PATH
)
leisure_instance.leisure_distributors = {}
leisure_instance.leisure_distributors['pump_latrines'] = PumpLatrineDistributor.from_config(pump_latrines=world.pump_latrines)
leisure_instance.leisure_distributors['distribution_centers'] = DistributionCenterDistributor.from_config(distribution_centers=world.distribution_centers)
leisure_instance.leisure_distributors['communals'] = CommunalDistributor.from_config(communals=world.communals)
leisure_instance.leisure_distributors['female_communals'] = FemaleCommunalDistributor.from_config(female_communals=world.female_communals)

#associate social activities to shelters
leisure_instance.distribute_social_venues_to_households(world.shelters)

simulator = CampSimulator.from_file(
    world = world,
    interaction = interaction,
    leisure = leisure_instance,
    policies = policies,
    config_filename = CONFIG_PATH,
)

leisure_instance.leisure_distributors

simulator.timer.reset()

simulator.run()
