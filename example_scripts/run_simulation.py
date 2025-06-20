"""June Epidemiology Simulation Runner

This script runs the June epidemiology simulation with configurable infection seeding.

Infection Seeding:
The simulation now uses a configurable YAML-based seeding system instead of hardcoded values.
The default configuration replicates the original 21 seeding events and is located at:
june/configs/defaults/epidemiology/infection_seeds/example_measles_outbreak.yaml

Usage:
  # Use default seeding configuration:
  python run_simulation.py
  
  # Use custom seeding configuration:
  python run_simulation.py --seeding_config path/to/custom_config.yaml
  
  # Use simple default config:
  python run_simulation.py --seeding_config defaults/epidemiology/infection_seeds/simple_default.yaml
"""

from ast import arg
import os
import cProfile
import pstats
import shutil
import logging
import numpy as np
import numba as nb
import random
import json
from pathlib import Path
import h5py
import sys
import argparse
import traceback

import pandas as pd
import yaml
from june.mpi_wrapper import MPI, mpi_comm, mpi_rank, mpi_size, mpi_available

from june.epidemiology.infection.disease_config import DiseaseConfig
from june.global_context import GlobalContext
from june.interaction import Interaction
from june.epidemiology.infection import (
    InfectionSelector,
    InfectionSelectors
)
from june.groups.travel import Travel
from june.groups.leisure import generate_leisure_for_config
from june.simulator import Simulator
from june.epidemiology.epidemiology import Epidemiology
from june.epidemiology.infection_seed import (
    InfectionSeed,
    InfectionSeeds
)
from june.epidemiology.infection_seed.infection_seeds_config_loader import(
    SeedingConfigLoader
)
from june.epidemiology.vaccines.vaccination_campaign import (
    VaccinationCampaigns
)
from june.policy import Policies
from june.event import Events
from june import paths
from june.records import Record
from june.domains import Domain, DomainSplitter

from june.tracker.tracker import Tracker

# Initialise rank properly based on MPI availability
if mpi_available:
    rank = MPI.COMM_WORLD.Get_rank()
else:
    rank = 0

# Path to the results folder
results_folder = "results"
rat_folder = "rat_outputs"

# Delete the results folder if it exists
if mpi_rank == 0:  # This works the same in both MPI and non-MPI modes
    if os.path.isdir(results_folder):
        shutil.rmtree(results_folder)
        if os.path.isdir(rat_folder):
            shutil.rmtree(rat_folder)
        print(f"'{results_folder}' folder has been deleted.")
    else:
        print(f"'{results_folder}' folder does not exist.") 

def print_attributes(obj, indent=0):
    """Recursively prints the attributes of an object."""
    space = "  " * indent
    if hasattr(obj, "__dict__"):
        for attr, value in vars(obj).items():
            if hasattr(value, "__dict__"):  # If the value is another object
                print(f"{space}{attr}:")
                print_attributes(value, indent + 1)
            else:
                print(f"{space}{attr}: {value}")
    else:
        print(f"{space}{obj}")  # Print primitive types or objects without attributes

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

# disable logging for ranks other than 0 when using MPI
#if mpi_rank > 0:
#    logging.disable(logging.CRITICAL)


def keys_to_int(x):
    return {int(k): v for k, v in x.items()}


# =============== Argparse =========================#

def str_to_bool(value):
    return value.lower() == "true"

parser = argparse.ArgumentParser(description="Full run of England")

parser.add_argument("-w", "--world_path", help="Path to saved world file", default="tests.hdf5")
parser.add_argument("-c", "--comorbidities", help="Include comorbidities", default="True")
parser.add_argument("-con", "--config", help="Config file", default=paths.configs_path / "config_simulation.yaml")
parser.add_argument(
    "-p", "--parameters",
    help="Parameter file",
    default=None  
)
parser.add_argument("-tr", "--tracker", help="Activate Tracker for CM tracing", default="False")
parser.add_argument("-ro", "--region_only", help="Run only one region", default="False")
parser.add_argument("-hb", "--household_beta", help="Household beta", type=float, default=0.25)
parser.add_argument("-nnv", "--no_vaccines", help="Implement no vaccine policies", default="False")
parser.add_argument("-v", "--vaccines", help="Implement vaccine policies", default="False")
parser.add_argument("-nv", "--no_visits", help="No shelter visits", default="False")
parser.add_argument("-ih", "--indoor_beta_ratio", help="Indoor/household beta ratio scaling", type=float, default=0.55)
parser.add_argument("-oh", "--outdoor_beta_ratio", help="Outdoor/household beta ratio scaling", type=float, default=0.05)
parser.add_argument("-inf", "--infectiousness_path", help="Path to infectiousness parameter file", default="nature")
parser.add_argument("-cs", "--child_susceptibility", help="Reduce child susceptibility for under 12s", default="False")
parser.add_argument("-u", "--isolation_units", help="Include isolation units", default="False")
parser.add_argument("-t", "--isolation_testing", help="Mean testing time", type=int, default=3)
parser.add_argument("-i", "--isolation_time", help="Isolation time", type=int, default=7)
parser.add_argument("-ic", "--isolation_compliance", help="Isolation compliance", type=float, default=0.6)
parser.add_argument("-m", "--mask_wearing", help="Include mask wearing", default="False")
parser.add_argument("-mc", "--mask_compliance", help="Mask wearing compliance", default="False")
parser.add_argument("-mb", "--mask_beta_factor", help="Mask beta factor reduction", type=float, default=0.5)
parser.add_argument("-s", "--save_path", help="Path to save results", default="results")
parser.add_argument("--n_seeding_days", help="Number of seeding days", type=int, default=10)
parser.add_argument("--n_seeding_case_per_day", help="Number of seeding cases per day", type=int, default=10)
parser.add_argument("--seeding_config", help="Path to seeding configuration YAML file (optional, uses default if not specified)", default=None)
# New argument for disabling MPI
parser.add_argument("--disable_mpi", help="Disable MPI even if available", action="store_true")

args = parser.parse_args()
args.save_path = Path(args.save_path)

def load_config(config_path):
    """Load yaml configuration file"""
    with open(config_path) as f:
        return yaml.load(f, Loader=yaml.FullLoader)
    
CONFIG_PATH = args.config
config = load_config(CONFIG_PATH)

disease_settings = config.get("disease")
disease = disease_settings.get("model")

parameters_path = args.parameters
if parameters_path is None:
    parameters_path = paths.configs_path / f"defaults/interaction/interaction_{disease}.yaml"

disease_config = DiseaseConfig(disease)
GlobalContext.set_disease_config(disease_config)

# Override MPI availability if requested
if args.disable_mpi and mpi_available:
    print("MPI support is available but disabled by command line argument")
    # We can't change the imported variables, but we can adjust behaviour

# Create unique save path if it already exists (only on rank 0 or in non-MPI mode)
if mpi_rank == 0:
    base_path = args.save_path
    counter = 1
    while args.save_path.exists():
        args.save_path = Path(f"{base_path}_{counter}")
        counter += 1
    args.save_path.mkdir(parents=True, exist_ok=False)

# Broadcast save path from rank 0 to other ranks in MPI mode
if mpi_available:
    # Only needed in MPI mode
    mpi_comm.Barrier()
    args.save_path = mpi_comm.bcast(args.save_path, root=0)
    mpi_comm.Barrier()

# Convert boolean-like arguments
bool_args = [
    "tracker", "comorbidities", "child_susceptibility", "no_vaccines",
    "vaccines", "no_visits", "isolation_units", "mask_wearing"
]
for attr in bool_args:
    setattr(args, attr, str_to_bool(getattr(args, attr)))

# Infectiousness path mapping
infectiousness_paths = {
    "nature": paths.configs_path / "defaults/transmission/nature.yaml",
    "correction_nature": paths.configs_path / "defaults/transmission/correction_nature.yaml",
    "nature_larger": paths.configs_path / "defaults/transmission/nature_larger_presymptomatic_transmission.yaml",
    "nature_lower": paths.configs_path / "defaults/transmission/nature_lower_presymptomatic_transmission.yaml",
    "xnexp": paths.configs_path / "defaults/transmission/XNExp.yaml",
}

if args.infectiousness_path in infectiousness_paths:
    transmission_config_path = infectiousness_paths[args.infectiousness_path]
else:
    raise NotImplementedError(f"Unknown infectiousness path: {args.infectiousness_path}")

# Print configuration if master process
if mpi_rank == 0:
    for key, value in vars(args).items():
        print(f"{key}: {value}")


# Configure logging
logger = logging.getLogger("run_simulation")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("run_simulation.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger.info("Starting simulation process")

# =============== world creation =========================#
CONFIG_PATH = args.config


def generate_simulator():
    try:
        logger.info("Initializing record")
        record = Record(
            record_path=args.save_path, record_static_data=True, mpi_rank=mpi_rank
        )
        
        # Domain decomposition is different in MPI vs non-MPI modes
        logger.info("Loading world from HDF5")
        if mpi_available and mpi_size > 1:
            # MPI mode with multiple processes
            if mpi_rank == 0:
                with h5py.File(args.world_path, "r") as f:
                    super_area_ids = f["geography"]["super_area_id"]
                    super_area_names = f["geography"]["super_area_name"]
                    super_area_name_to_id = {
                        name.decode(): id for name, id in zip(super_area_names, super_area_ids)
                    }
                super_areas_per_domain, score_per_domain = DomainSplitter.generate_world_split(
                    number_of_domains=mpi_size, world_path=args.world_path
                )
                super_area_names_to_domain_dict = {}
                super_area_ids_to_domain_dict = {}
                for domain, super_areas in super_areas_per_domain.items():
                    for super_area in super_areas:
                        super_area_names_to_domain_dict[super_area] = domain
                        super_area_ids_to_domain_dict[
                            int(super_area_name_to_id[super_area])
                        ] = domain
                with open("super_area_ids_to_domain.json", "w") as f:
                    json.dump(super_area_ids_to_domain_dict, f)
                with open("super_area_names_to_domain.json", "w") as f:
                    json.dump(super_area_names_to_domain_dict, f)
                    
            print(f"mpi_rank {mpi_rank} waiting")
            if mpi_available:
                mpi_comm.Barrier()
                
            if mpi_rank > 0:
                with open("super_area_ids_to_domain.json", "r") as f:
                    super_area_ids_to_domain_dict = json.load(f, object_hook=keys_to_int)
            print(f"mpi_rank {mpi_rank} loading domain")
            
            domain = Domain.from_hdf5(
                domain_id=mpi_rank,
                super_areas_to_domain_dict=super_area_ids_to_domain_dict,
                hdf5_file_path=args.world_path,
                interaction_config=args.parameters,
            )
        else:
            # Non-MPI mode or single MPI process - load entire world
            logger.info("Loading entire world in a single domain")
            
            # For non-MPI mode, we create a simple domain dict that assigns everything to domain 0
            with h5py.File(args.world_path, "r") as f:
                super_area_ids = f["geography"]["super_area_id"]
                super_area_names = f["geography"]["super_area_name"]
                # Decode the byte strings to regular strings
                super_area_names_decoded = [name.decode('utf-8') for name in super_area_names]

                # Create a dictionary mapping super area IDs to names
                super_area_ids_to_names_dict = {int(id): name.decode('utf-8') for id, name in zip(super_area_ids, super_area_names)}
                print(super_area_ids_to_names_dict)
                # Create a dictionary mapping all super areas to domain 0
                super_area_ids_to_domain_dict = {int(id): 0 for id in super_area_ids}
            domain = Domain.from_hdf5(
                domain_id=0,
                super_areas_to_domain_dict=super_area_ids_to_domain_dict,
                hdf5_file_path=args.world_path,
                interaction_config=args.parameters,
            )
        
        print(f"mpi_rank {mpi_rank} has loaded domain")
        logger.info(f"Domain loaded successfully for rank {mpi_rank}")
        
        # Regenerate leisure
        logger.info("Generating leisure activities")
        try:
            leisure = generate_leisure_for_config(domain, CONFIG_PATH)
            logger.info("Leisure activities generated successfully")
        except Exception as e:
            logger.warning(f"Error generating leisure activities: {e}")
            logger.warning("Continuing without leisure activities")
            leisure = None

        # Initialize disease model
        logger.info("Setting up disease model and infection selectors")
        disease_config = GlobalContext.get_disease_config() 
        try:
            selector = InfectionSelector.from_disease_config(disease_config)
            selectors = InfectionSelectors([selector])
            logger.info("Infection selectors initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing infection selectors: {e}")
            raise

        # Initialize infection seed from configuration
        logger.info("Setting up infection seed from configuration")
        try:
            # Load configuration using the from_file class method
            loader = SeedingConfigLoader.from_file(args.seeding_config)
            
            # Validate configuration
            errors = loader.validate_config()
            if errors:
                error_msg = "Configuration validation failed:\n" + "\n".join(errors)
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Print summary
            loader.print_summary()
            
            # Create infection seeds
            infection_seeds = loader.create_infection_seeds(domain, selector)
            logger.info("Infection seeds initialized successfully from configuration")
            
        except Exception as e:
            logger.error(f"Error initializing infection seeds from configuration: {e}")

        # Initialize vaccination campaigns
        logger.info("Setting up vaccination campaigns")
        try:
            vaccination_campaigns = VaccinationCampaigns.from_disease_config(disease_config)
            logger.info("Vaccination campaigns initialized successfully")
        except Exception as e:
            logger.warning(f"Error initializing vaccination campaigns: {e}")
            logger.warning("Continuing without vaccination campaigns")
            vaccination_campaigns = None

        # Initialize epidemiology
        logger.info("Setting up epidemiology")
        epidemiology = Epidemiology(
            infection_selectors=selectors, infection_seeds=infection_seeds, vaccination_campaigns=vaccination_campaigns
        )
        logger.info("Epidemiology initialized successfully")
        

        # Print details of the Epidemiology object
        logger.info("=== Epidemiology Object Initialized: ===")
        logger.info(f"Object Type: {type(epidemiology)}")
        
        # Initialize interaction
        logger.info("Setting up interaction model")
        try:
            interaction = Interaction.from_file()
            logger.info("Interaction model initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing interaction model: {e}")
            raise

        # Initialize policies
        logger.info("Setting up policies")
        try:
            # Get policy data from disease_config for inspection
            policy_data = disease_config.policy_manager.get_all_policies()
            logger.info(f"Found {len(policy_data)} policy entries in configuration")
            
            # Print policies to inspect
            for policy_name, policy_config in policy_data.items():
                logger.info(f"Policy: {policy_name}, Config: {type(policy_config)}")
            
            # Now try to initialize policies
            # Load policies using only june.policy
            policies = Policies.from_file(
                disease_config=disease_config,
                base_policy_modules=("june.policy",)  # Remove camps.policy
            )
            logger.info("Policies initialized successfully")
            logger.info(f"Loaded {len(policies.policies)} policies")
        except Exception as e:
            logger.error(f"Error initializing policies: {e}")
            logger.error("Full traceback:", exc_info=True)
            logger.warning("Continuing without policies")
            policies = None

        # Initialize events
        logger.info("Setting up events")
        try:
            events = Events.from_file()
            logger.info("Events initialized successfully")
        except Exception as e:
            logger.warning(f"Error initializing events: {e}")
            logger.warning("Continuing without events")
            events = None

        # Initialize travel
        logger.info("Setting up travel")
        try:
            travel = Travel()
            logger.info("Travel initialized successfully")
        except Exception as e:
            logger.warning(f"Error initializing travel: {e}")
            logger.warning("Continuing without travel")
            travel = None

        # Inspect domain venues
        group_types = []
        domainVenues = {}

        # Define a mapping of domain attributes and a flag indicating if "bins" is required
        venue_attributes = {
            "households": True,
            "care_homes": True,
            "schools": True,
            "hospitals": False,
            "companies": True,
            "universities": True,
            "pubs": True,
            "groceries": True,
            "cinemas": True,
            "gyms": True,
            "city_transports": False,
            "inter_city_transports": False,
        }

        # Log venue information
        logger.info("Inspecting domain venues")
        for venue, has_bins in venue_attributes.items():
            venue_data = getattr(domain, venue, None)
            if venue_data is not None:
                if len(venue_data) > 0:
                    group_types.append(venue_data)
                    domainVenues[venue] = {
                        "N": len(venue_data),
                        "bins": venue_data[0].subgroup_bins if has_bins else None,
                    }
                    logger.info(f"Found {len(venue_data)} {venue}")
                else:
                    domainVenues[venue] = {"N": 0, "bins": "NaN" if has_bins else None}
                    logger.info(f"No {venue} found")
            else:
                logger.info(f"No {venue} attribute in domain")
        
        logger.info("Domain venue inspection complete")

        # Initialize tracker if requested
        if args.tracker:
            logger.info("Setting up tracker")
            try:
                tracker = Tracker(
                    world=domain,
                    record_path=args.save_path,
                    group_types=group_types,
                    load_interactions_path=args.parameters,
                    contact_sexes=["unisex", "male", "female"],
                    MaxVenueTrackingsize=100000,
                )
                tracker.print_tracker_initialization()
                logger.info("Tracker initialized successfully")
            except Exception as e:
                logger.warning(f"Error initializing tracker: {e}")
                logger.warning("Continuing without tracker")
                tracker = None
        else:
            tracker = None

        # Initialize simulator
        logger.info("Creating simulator")
        simulator = Simulator.from_file(
            world=domain,
            policies=policies,
            events=events,
            interaction=interaction,
            leisure=leisure,
            travel=travel,
            epidemiology=epidemiology,
            config_filename=CONFIG_PATH,
            record=record,
            tracker=tracker
        )
    
        logger.info("SIMULATOR GENERATED SUCCESSFULLY!")
        return simulator
        
    except Exception as e:
        logger.error(f"Error generating simulator: {e}")
        logger.error(traceback.format_exc())
        raise


# ==================================================================================#

# =================================== simulator ===============================#

profiler = cProfile.Profile()
profiler.enable()

logger.info(f"mpi_rank {mpi_rank} generate simulator")
try:
    simulator = generate_simulator()

    logger.info("Starting simulation run")
    simulator.run()
    logger.info("Simulation completed successfully")
except Exception as e:
    logger.error(f"Error running simulation: {e}")
    logger.error(traceback.format_exc())

# Save profiling information
try:
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumulative')
    profile_filename = f'simulation_profile_rank_{rank}.stats'
    stats.dump_stats(profile_filename)
    logger.info(f"Performance profiling data saved to {profile_filename}")
except Exception as e:
    logger.error(f"Failed to save profiling data: {e}")

logger.info("Script execution completed")