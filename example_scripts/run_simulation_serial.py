import numpy as np
import random
import numba as nb
import pandas as pd
import time
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import sys
import argparse
from pathlib import Path
import yaml

from collections import defaultdict

from june import World
from june.geography import Geography
from june.demography import Demography
from june.interaction import Interaction
from june.epidemiology.epidemiology import Epidemiology
from june.epidemiology.infection import Infection, InfectionSelector, InfectionSelectors
from june.epidemiology.infection.health_index import Data2Rates
from june.epidemiology.infection.health_index.health_index import HealthIndexGenerator
from june.epidemiology.infection.transmission import TransmissionConstant
from june.groups import (
    Hospitals,
    Schools,
    Companies,
    Households,
    CareHomes,
    Cemeteries,
    Universities,
)
from june.groups.leisure import (
    generate_leisure_for_config,
    Cinemas,
    Pubs,
    Groceries,
    Gyms,
)
from june.groups.travel import Travel
from june.groups.travel.transport import (
    CityTransport,
    CityTransports,
    InterCityTransport,
    InterCityTransports,
)
from june.simulator import Simulator
from june.epidemiology.infection_seed import InfectionSeed, InfectionSeeds
from june.policy import Policy, Policies
from june import paths
from june.hdf5_savers import load_geography_from_hdf5
from june.records import Record, RecordReader

from june.world import generate_world_from_geography
from june.hdf5_savers import generate_world_from_hdf5

from june.tracker.tracker import Tracker
from june.tracker.tracker_plots import PlotClass

from june.activity import ActivityManager


def set_random_seed(seed=999):
    """
    Sets global seeds for testing in numpy, random, and numbaized numpy.
    """

    @nb.njit(cache=True)
    def set_seed_numba(seed):
        random.seed(seed)
        return np.random.seed(seed)

    np.random.seed(seed)
    set_seed_numba(seed)
    random.seed(seed)
    return


set_random_seed(0)

# =============== Argparse =========================#

parser = argparse.ArgumentParser(description="Full run of the England")

parser.add_argument(
    "-w",
    "--world_path",
    help="path to saved world file",
    required=False,
    default="/cosma5/data/do010/dc-walk3/world.hdf5",
)

parser.add_argument(
    "-c",
    "--comorbidities",
    help="True to include comorbidities",
    required=False,
    default="True",
)
parser.add_argument(
    "-con",
    "--config",
    help="Config file",
    required=False,
    default=paths.configs_path / "config_example.yaml",
)
parser.add_argument(
    "-p",
    "--parameters",
    help="Parameter file",
    required=False,
    default=paths.configs_path / "defaults/interaction/interaction.yaml",
)

parser.add_argument(
    "-tr",
    "--tracker",
    help="Activate Tracker for CM tracing",
    required=False,
    default="False",
)

parser.add_argument(
    "-ro", "--region_only", help="Run only one region", required=False, default="False"
)

parser.add_argument(
    "-hb", "--household_beta", help="Household beta", required=False, default=0.25
)
parser.add_argument(
    "-nnv",
    "--no_vaccines",
    help="Implement no vaccine policies",
    required=False,
    default="False",
)
parser.add_argument(
    "-v",
    "--vaccines",
    help="Implement vaccine policies",
    required=False,
    default="False",
)
parser.add_argument(
    "-nv", "--no_visits", help="No shelter visits", required=False, default="False"
)
parser.add_argument(
    "-ih",
    "--indoor_beta_ratio",
    help="Indoor/household beta ratio scaling",
    required=False,
    default=0.55,
)
parser.add_argument(
    "-oh",
    "--outdoor_beta_ratio",
    help="Outdoor/household beta ratio scaling",
    required=False,
    default=0.05,
)
parser.add_argument(
    "-inf",
    "--infectiousness_path",
    help="path to infectiousness parameter file",
    required=False,
    default="nature",
)
parser.add_argument(
    "-cs",
    "--child_susceptibility",
    help="Reduce child susceptibility for under 12s",
    required=False,
    default="False",
)
parser.add_argument(
    "-u",
    "--isolation_units",
    help="True to include isolation units",
    required=False,
    default="False",
)
parser.add_argument(
    "-t", "--isolation_testing", help="Mean testing time", required=False, default=3
)
parser.add_argument(
    "-i", "--isolation_time", help="Ouput file name", required=False, default=7
)
parser.add_argument(
    "-ic",
    "--isolation_compliance",
    help="Isolation unit self reporting compliance",
    required=False,
    default=0.6,
)
parser.add_argument(
    "-m",
    "--mask_wearing",
    help="True to include mask wearing",
    required=False,
    default="False",
)
parser.add_argument(
    "-mc",
    "--mask_compliance",
    help="Mask wearing compliance",
    required=False,
    default="False",
)
parser.add_argument(
    "-mb",
    "--mask_beta_factor",
    help="Mask beta factor reduction",
    required=False,
    default=0.5,
)

parser.add_argument(
    "-s",
    "--save_path",
    help="Path of where to save logger",
    required=False,
    default="results",
)

parser.add_argument(
    "--n_seeding_days", help="number of seeding days", required=False, default=10
)
parser.add_argument(
    "--n_seeding_case_per_day",
    help="number of seeding cases per day",
    required=False,
    default=10,
)

args = parser.parse_args()
args.save_path = Path(args.save_path)

counter = 1
OG_save_path = args.save_path
while args.save_path.is_dir() == True:
    args.save_path = Path(str(OG_save_path) + "_%s" % counter)
    counter += 1
args.save_path.mkdir(parents=True, exist_ok=False)


if args.tracker == "True":
    args.tracker = True
else:
    args.tracker = False

if args.comorbidities == "True":
    args.comorbidities = True
else:
    args.comorbidities = False

if args.child_susceptibility == "True":
    args.child_susceptibility = True
else:
    args.child_susceptibility = False

if args.no_vaccines == "True":
    args.no_vaccines = True
else:
    args.no_vaccines = False

if args.vaccines == "True":
    args.vaccines = True
else:
    args.vaccines = False

if args.no_visits == "True":
    args.no_visits = True
else:
    args.no_visits = False

if args.isolation_units == "True":
    args.isolation_units = True
else:
    args.isolation_units = False

if args.mask_wearing == "True":
    args.mask_wearing = True
else:
    args.mask_wearing = False


if args.infectiousness_path == "nature":
    transmission_config_path = paths.configs_path / "defaults/transmission/nature.yaml"
elif args.infectiousness_path == "correction_nature":
    transmission_config_path = (
        paths.configs_path / "defaults/transmission/correction_nature.yaml"
    )
elif args.infectiousness_path == "nature_larger":
    transmission_config_path = (
        paths.configs_path
        / "defaults/transmission/nature_larger_presymptomatic_transmission.yaml"
    )
elif args.infectiousness_path == "nature_lower":
    transmission_config_path = (
        paths.configs_path
        / "defaults/transmission/nature_lower_presymptomatic_transmission.yaml"
    )
elif args.infectiousness_path == "xnexp":
    transmission_config_path = paths.configs_path / "defaults/transmission/XNExp.yaml"
else:
    raise NotImplementedError

print("Comorbidities set to: {}".format(args.comorbidities))
print("Parameters path set to: {}".format(args.parameters))
print("Indoor beta ratio is set to: {}".format(args.indoor_beta_ratio))
print("Outdoor beta ratio set to: {}".format(args.outdoor_beta_ratio))
print("Infectiousness path set to: {}".format(args.infectiousness_path))
print("Child susceptibility change set to: {}".format(args.child_susceptibility))

print("Isolation units set to: {}".format(args.isolation_units))
print("Household beta set to: {}".format(args.household_beta))
if args.isolation_units:
    print("Testing time set to: {}".format(args.isolation_testing))
    print("Isolation time set to: {}".format(args.isolation_time))
    print("Isolation compliance set to: {}".format(args.isolation_compliance))

print("Mask wearing set to: {}".format(args.mask_wearing))
if args.mask_wearing:
    print("Mask compliance set to: {}".format(args.mask_compliance))
    print("Mask beta factor set up: {}".format(args.mask_beta_factor))

print("World path set to: {}".format(args.world_path))
print("Save path set to: {}".format(args.save_path))

print("\n", args.__dict__, "\n")


time.sleep(10)

# =============== world creation =========================#
CONFIG_PATH = args.config


world = generate_world_from_hdf5(args.world_path, interaction_config=args.parameters)

leisure = generate_leisure_for_config(world, CONFIG_PATH)
travel = Travel()

# ==================================================================================#

# =================================== Infection ===============================#


selector = InfectionSelector.from_file()
selectors = InfectionSelectors([selector])

infection_seed = InfectionSeed.from_uniform_cases(
    world=world,
    infection_selector=selector,
    cases_per_capita=0.01,
    date="2020-03-02 9:00",
    seed_past_infections=False,
)
infection_seeds = InfectionSeeds([infection_seed])

epidemiology = Epidemiology(
    infection_selectors=selectors, infection_seeds=infection_seeds
)

interaction = Interaction.from_file(config_filename=args.parameters)
# ============================================================================#

# =================================== policies ===============================#


policies = Policies.from_file(
    paths.configs_path / "defaults/policy/policy.yaml",
    base_policy_modules=("june.policy", "camps.policy"),
)

print(
    "Policy path set to: {}".format(paths.configs_path / "defaults/policy/policy.yaml")
)

record = Record(record_path=args.save_path, record_static_data=True)

# ==================================================================================#

# =================================== tracker ===============================#
if args.tracker:
    group_types = [
        world.households,
        world.care_homes,
        world.schools,
        world.hospitals,
        world.companies,
        world.universities,
        world.pubs,
        world.groceries,
        world.cinemas,
        world.gyms,
        world.city_transports,
        world.inter_city_transports,
    ]

    tracker = Tracker(
        world=world,
        record_path=args.save_path,
        group_types=group_types,
        load_interactions_path=args.parameters,
        contact_sexes=["unisex", "male", "female"],
        Tracker_Contact_Type=["1D"],
        MaxVenueTrackingSize=10000,
    )
else:
    tracker = None

# ==================================================================================#

# =================================== simulator ===============================#


simulator = Simulator.from_file(
    world=world,
    epidemiology=epidemiology,
    interaction=interaction,
    config_filename=CONFIG_PATH,
    leisure=leisure,
    travel=travel,
    record=record,
    policies=policies,
    tracker=tracker,
)

simulator.run()

# ==================================================================================#

# =================================== read logger ===============================#

read = RecordReader(args.save_path)

infections_df = read.get_table_with_extras("infections", "infected_ids")

locations_df = infections_df.groupby(["location_specs", "timestamp"]).size()

locations_df.to_csv(args.save_path / "locations.csv")

# ==================================================================================#

# =================================== tracker figures ===============================#

if args.tracker:
    print("Tracker stuff now")
    simulator.tracker.contract_matrices("AC", np.array([0, 18, 100]))
    simulator.tracker.contract_matrices(
        "Paper",
        [0, 5, 10, 13, 15, 18, 20, 22, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 100],
    )
    simulator.tracker.post_process_simulation(save=True)

    # Make Plots
    Plots = PlotClass(record_path=args.save_path / "Tracker", Tracker_Contact_Type="1D")
    Plots.make_plots(
        plot_BBC=True,
        plot_thumbprints=True,
        SameCMAP="Log",
        plot_INPUTOUTPUT=True,
        plot_AvContactsLocation=True,
        plot_dTLocationPopulation=True,
        plot_InteractionMatrices=True,
        plot_ContactMatrices=True,
        plot_CompareSexMatrices=True,
        plot_AgeBinning=True,
        plot_Distances=True,
    )

    ##Make Plots
    # Plots = PlotClass(
    #    record_path=args.save_path / "Tracker",
    #    Tracker_Contact_Type = "All"
    # )
    # Plots.make_plots(
    #    plot_BBC = True,
    #    plot_thumbprints = True,
    #    SameCMAP="Log",

    #    plot_INPUTOUTPUT=False,
    #    plot_AvContactsLocation=False,
    #    plot_dTLocationPopulation=False,
    #    plot_InteractionMatrices=True,
    #    plot_ContactMatrices=True,
    #    plot_CompareSexMatrices=True,
    #    plot_AgeBinning=False,
    #    plot_Distances=False
    # )
