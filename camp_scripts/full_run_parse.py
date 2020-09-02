import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import time
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import sys
import argparse
from pathlib import Path

from june.demography.geography import Geography
from june.demography.demography import (
    load_age_and_sex_generators_for_bins,
    Demography,
    Population,
    load_comorbidity_data,
    generate_comorbidity,
)
from june.paths import data_path, configs_path
from june.infection import Infection, HealthIndexGenerator
from june.infection_seed import InfectionSeed
from june.infection import InfectionSelector
from june.interaction import Interaction
from june.groups import Hospital, Hospitals
from june.distributors import HospitalDistributor
from june.hdf5_savers import generate_world_from_hdf5
from june.groups import Cemeteries
from june.policy import Policy, Policies
from june.logger.read_logger import ReadLogger
from june.simulator import Simulator

from camps.activity import CampActivityManager
from camps.paths import camp_data_path, camp_configs_path
from camps.world import World
from camps.groups.leisure import generate_leisure_for_world, generate_leisure_for_config
from camp_creation import (
    generate_empty_world,
    populate_world,
    distribute_people_to_households,
)  # this is loaded from the ../camp_scripts folder

from camps.groups import PumpLatrines, PumpLatrineDistributor
from camps.groups import DistributionCenters, DistributionCenterDistributor
from camps.groups import Communals, CommunalDistributor
from camps.groups import FemaleCommunals, FemaleCommunalDistributor
from camps.groups import Religiouss, ReligiousDistributor
from camps.groups import Shelter, Shelters, ShelterDistributor
from camps.groups import IsolationUnit, IsolationUnits
from camps.groups import LearningCenters 
from camps.distributors import LearningCenterDistributor
from camps.groups import PlayGroups, PlayGroupDistributor 
from camps.groups import EVouchers, EVoucherDistributor
from camps.groups import NFDistributionCenters, NFDistributionCenterDistributor

from june.groups.leisure import HouseholdVisitsDistributor

#=============== Argparse =========================#

parser = argparse.ArgumentParser(description='Full run of the camp')

parser.add_argument('-c', '--comorbidities', help="True to include comorbidities", required=False, default="True")
parser.add_argument('-p', '--parameters', help="Parameter file", required=False, default="ContactInteraction_med_low_low_low.yaml")
parser.add_argument('-u', '--isolation_units', help="True to include isolation units", required=False, default="False")
parser.add_argument('-t', '--isolation_testing', help="Model weights in HDF5 format", required=False, default=3)
parser.add_argument('-i', '--isolation_time', help="Ouput file name", required=False, default=7)
parser.add_argument('-ic', '--isolation_compliance', help="Isolation unit self reporting compliance", required=False, default=0.6)
parser.add_argument('-m', '--mask_wearing', help="True to include mask wearing", required=False, default="False")
parser.add_argument('-mc', '--mask_compliance', help="Mask wearing compliance", required=False, default="False")
parser.add_argument('-mb', '--mask_beta_factor', help="Mask beta factor reduction", required=False, default=0.5)
parser.add_argument('-inf', '--infectiousness_path', help="path to infectiousness parameter file", required=False, default='nature')
parser.add_argument('-s', '--save_path', help="Path of where to save logger", required=False, default="results")
parser.add_argument('-lc', '--learning_centers' ,help="Add learning centers", required=False, default=False)
args = parser.parse_args()

if args.comorbidities == "True":
    args.comorbidities = True
else:
    args.comorbidities = False

if args.isolation_units == "True":
    args.isolation_units = True
else:
    args.isolation_units = False

if args.mask_wearing == "True":
    args.mask_wearing = True
else:
    args.mask_wearing = False
    
if args.infectiousness_path == 'nature':
    transmission_config_path = camp_configs_path / 'defaults/transmission/nature.yaml'
elif args.infectiousness_path == 'correction_nature':
    transmission_config_path = camp_configs_path / 'defaults/transmission/correction_nature.yaml'
elif args.infectiousness_path == 'nature_larger':
    transmission_config_path = camp_configs_path / 'defaults/transmission/nature_larger_presymptomatic_transmission.yaml'
elif args.infectiousness_path == 'nature_lower':
    transmission_config_path = camp_configs_path / 'defaults/transmission/nature_lower_presymptomatic_transmission.yaml'
else:
    raise NotImplementedError

print ('Comorbidities set to: {}'.format(args.comorbidities))
print ('Parameters path set to: {}'.format(args.parameters))
print ('Isolation units set to: {}'.format(args.isolation_units))
print ('Testing time set to: {}'.format(args.isolation_testing))
print ('Isolation time set to: {}'.format(args.isolation_time))
print ('Isolation compliance set to: {}'.format(args.isolation_compliance))
print ('Save path set to: {}'.format(args.save_path))

#=============== world creation =========================#
CONFIG_PATH = camp_configs_path / "config_example.yaml"

# create empty world's geography
#world = generate_empty_world({"super_area": ["CXB-219-C"]})
world = generate_empty_world({"region": ["CXB-219", "CXB-217"]})
#world = generate_empty_world()

# populate empty world
populate_world(world)

# distribute people to households
distribute_people_to_households(world)

# medical facilities
hospitals = Hospitals.from_file(
    filename=camp_data_path / "input/hospitals/hospitals.csv"
)
world.hospitals = hospitals
for hospital in world.hospitals:
    hospital.super_area = world.super_areas.members[0]
hospital_distributor = HospitalDistributor(
    hospitals, medic_min_age=20, patients_per_medic=10
)
world.isolation_units = IsolationUnits([IsolationUnit()])

hospital_distributor.distribute_medics_from_world(world.people)

if args.learning_centers:
    world.learning_centers = LearningCenters.for_areas(
                        world.areas,
                        n_shifts=4
    )
    learning_center_distributor = LearningCenterDistributor.from_file(
    learning_centers=world.learning_centers
    )
    learning_center_distributor.distribute_kids_to_learning_centers(world.areas)
    learning_center_distributor.distribute_teachers_to_learning_centers(world.areas)
    CONFIG_PATH = camp_configs_path / "learning_center_config.yaml"



world.pump_latrines = PumpLatrines.for_areas(world.areas)
world.play_groups = PlayGroups.for_areas(world.areas)
world.distribution_centers = DistributionCenters.for_areas(world.areas)
world.communals = Communals.for_areas(world.areas)
world.female_communals = FemaleCommunals.for_areas(world.areas)
world.religiouss = Religiouss.for_areas(world.areas)
world.e_vouchers = EVouchers.for_areas(world.areas)
world.n_f_distribution_centers = NFDistributionCenters.for_areas(world.areas)

print("Total people = ", len(world.people))
print("Mean age = ", np.mean([person.age for person in world.people]))
# world.box_mode = False
world.cemeteries = Cemeteries()

world.shelters = Shelters.for_areas(world.areas)
shelter_distributor = ShelterDistributor(
    sharing_shelter_ratio=0.75
)  # proportion of families that share a shelter
for area in world.areas:
    shelter_distributor.distribute_people_in_shelters(area.shelters, area.households)

# ============================================================================#

# =================================== comorbidities ===============================#

if args.comorbidities:

    comorbidity_data = load_comorbidity_data(camp_data_path / "input/demography/myanmar_male_comorbidities.csv",\
                                              camp_data_path / "input/demography/myanmar_female_comorbidities.csv"
    )
    for person in world.people:
        person.comorbidity = generate_comorbidity(person, comorbidity_data)

    health_index_generator = HealthIndexGenerator.from_file_with_comorbidities(
        camp_configs_path / 'defaults/comorbidities.yaml',
        camp_data_path / 'input/demography/uk_male_comorbidities.csv',
        camp_data_path / 'input/demography/uk_female_comorbidities.csv',
        asymptomatic_ratio=0.2
    )


else:
    health_index_generator = HealthIndexGenerator.from_file(asymptomatic_ratio=0.2)

# ============================================================================#

# =================================== policies ===============================#

if args.isolation_units:
    policies = Policies.from_file(
        camp_configs_path / "defaults/policy/isolation.yaml",
        base_policy_modules=("june.policy", "camps.policy"),
    )

    policies.policies[3].n_quarantine_days = args.isolation_time
    policies.policies[3].testing_mean_time = args.isolation_testing
    policies.policies[3].compliance = args.isolation_compliance

elif args.mask_wearing:
    policies = Policies.from_file(
        camp_configs_path / "defaults/policy/mask_wearing.yaml",
        base_policy_modules=("june.policy", "camps.policy"),
    )

    policies.policies[4].compliance = args.mask_compliance
    policies.policies[4].beta_factor = args.mask_beta_factor
    
else:
    policies = Policies.from_file(
        camp_configs_path / "defaults/policy/home_care_policy.yaml",
        base_policy_modules=("june.policy", "camps.policy"),
    )

# ============================================================================#

# =================================== infection ===============================#


selector = InfectionSelector.from_file(health_index_generator=health_index_generator,
        transmission_config_path=transmission_config_path)

interaction = Interaction.from_file(
    config_filename=camp_configs_path
    / "defaults/interaction/" / args.parameters,
)


cases_detected = {
    "CXB-202": 3,
    "CXB-204": 6,
    "CXB-208": 8,
    "CXB-203": 1,
    "CXB-207": 2,
    "CXB-213": 2,
}  # By the 24th May

print("Detected cases = ", sum(cases_detected.values()))

msoa_region_filename = camp_data_path / "input/geography/area_super_area_region.csv"
msoa_region = pd.read_csv(msoa_region_filename)[["super_area", "region"]]
infection_seed = InfectionSeed(
    super_areas=world.super_areas, selector=selector, msoa_region=msoa_region
)

for key, n_cases in cases_detected.items():
    infection_seed.unleash_virus_regional_cases(key, n_cases * 10)
# Add some extra random cases
infection_seed.unleash_virus(n_cases=100)

print("Infected people in seed = ", len(world.people.infected))


# ==================================================================================#

# =================================== leisure config ===============================#
leisure_instance = generate_leisure_for_config(world=world, config_filename=CONFIG_PATH)
leisure_instance.leisure_distributors = {}
leisure_instance.leisure_distributors[
    "pump_latrines"
] = PumpLatrineDistributor.from_config(pump_latrines=world.pump_latrines)
leisure_instance.leisure_distributors[
    "play_groups"
] = PlayGroupDistributor.from_config(play_groups=world.play_groups)
leisure_instance.leisure_distributors[
    "distribution_centers"
] = DistributionCenterDistributor.from_config(
    distribution_centers=world.distribution_centers
)
leisure_instance.leisure_distributors[
    "communals"
] = CommunalDistributor.from_config(
    communals=world.communals
)
leisure_instance.leisure_distributors[
    "female_communals"
] = FemaleCommunalDistributor.from_config(
    female_communals=world.female_communals
)
leisure_instance.leisure_distributors[
    'religiouss'
] = ReligiousDistributor.from_config(religiouss=world.religiouss)
leisure_instance.leisure_distributors[
    'e_vouchers'
] = EVoucherDistributor.from_config(evouchers=world.e_vouchers)
leisure_instance.leisure_distributors[
    'n_f_distribution_centers'
] = NFDistributionCenterDistributor.from_config(
    nfdistributioncenters=world.n_f_distribution_centers
)

# associate social activities to shelters
leisure_instance.distribute_social_venues_to_households(world.shelters, world.super_areas)

# ==================================================================================#

# =================================== simulator ===============================#
Simulator.ActivityManager = CampActivityManager
simulator = Simulator.from_file(
    world=world,
    interaction=interaction,
    leisure=leisure_instance,
    policies=policies,
    config_filename=CONFIG_PATH,
    infection_selector=selector,
    save_path=args.save_path
)

leisure_instance.leisure_distributors

simulator.timer.reset()

simulator.run()

# ==================================================================================#
read = ReadLogger(output_path=args.save_path)
summary = read.run_summary(
    super_area_region_path=camp_data_path 
    / 'input/geography/area_super_area_region.csv'
)
summary.to_csv(Path(args.save_path) / 'summary.csv')
