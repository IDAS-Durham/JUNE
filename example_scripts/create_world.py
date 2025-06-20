import cProfile
import csv
import os
import pstats
import logging
import sys

import pandas as pd
from june.epidemiology.infection.disease_config import DiseaseConfig
from june.geography import Geography, Airports
from june.groups import Hospitals, Schools, Companies, CareHomes, Universities
from june.global_context import GlobalContext
from june.groups.leisure import (
    Pubs,
    Cinemas,
    Groceries,
    Gyms,
    generate_leisure_for_config,
)
from june.groups.travel import Travel
from june.world import generate_world_from_geography
from june.paths import configs_path, data_path

import time
import numpy as np

# Configure logging
logger = logging.getLogger("create_world")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("create_world.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger.info("Starting world creation process")

profiler = cProfile.Profile()
profiler.enable()

#==================== SETTING THE GEOGRAPHIC LOCATION =========================================
logger.info("Setting up geographic locations and boundaries")


#Select the geography to simulate 
#1 : ORIGINAL EXAMPLE (LONDON + BATH + CAMBRIDGE)
#2 : NORTHUMBERLAND (Run without hospitals or stations)
#3 : ENGLAND
#4 : NORTHUMBERLAND + TYNEWEAR
#5 : MERSEYSIDE
choice=1



if choice == 1: #ORIGINAL EXAMPLE (LONDON + BATH + CAMBRIDGE)
    file_path = os.path.join(os.path.dirname(__file__), "london_areas.txt")
    try:
        msoas_to_load = np.loadtxt(file_path, dtype=np.str_)[40:60]
        logger.info(f"Loaded {len(msoas_to_load)} London super areas")
    except Exception as e:
        logger.error(f"Failed to load London super areas: {e}")
        raise

    # add King's cross area for station
    if "E00004734" not in msoas_to_load:
        msoas_to_load = np.append(msoas_to_load, "E02000187")
        logger.info("Added King's cross area for station (E02000187)")
        
    # add some people commuting from Cambridge
    try:
        msoas_to_load = np.concatenate((msoas_to_load, ["E02003719", "E02003720", "E02003721"]))
        logger.info("Added Cambridge areas for commuting (E02003719, E02003720, E02003721)")
    except Exception as e:
        logger.warning(f"Could not add Cambridge areas: {e}")
    #
    # add Bath as well to have a city with no stations
    try:
        msoas_to_load = np.concatenate(
            (msoas_to_load, ["E02002988", "E02002989", "E02002990", "E02002991", "E02002992"])
        )
        logger.info("Added Bath areas (city with no stations)")
    except Exception as e:
        logger.warning(f"Could not add Bath areas: {e}")
elif choice == 2: #NORTHUMBERLAND (Run without hospitals or stations)
    file_path = os.path.join(os.path.dirname(__file__), "msoas/northumberland_MSOAs.txt")
    msoas_to_load = np.loadtxt(file_path, dtype=np.str_)
elif choice == 3: #ENGLAND RUN
    file_path = "data/input/geography/super_area_coordinates.csv"
    with open(file_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        msoas_to_load = [row['super_area'] for row in csv_reader if not row['super_area'].startswith('W')]
elif choice == 4: #NORTHUMBERLAND + TYNE AND WEAR
    file_path = os.path.join(os.path.dirname(__file__), "msoas/northumberland_MSOAs.txt")
    msoas_to_load = np.loadtxt(file_path, dtype=str)

    # Load the CSV file
    csv_file = os.path.join(os.path.dirname(__file__), "tyne-and-wear_MSOAs.csv")  # Adjust file name
    df = pd.read_csv(csv_file)

    # Extract existing MSOAs from CSV
    csv_msoas = df.iloc[:, 0].values  # Extract as a NumPy array

    # Combine the MSOAs together in one variable
    msoas = np.concatenate((csv_msoas, msoas_to_load))
elif choice == 5: #MERSEYSIDE
    file_path = os.path.join(os.path.dirname(__file__), "msoas/Merseyside_MSOAs.txt")
    msoas_to_load = np.loadtxt(file_path, dtype=np.str_)



#============================================================================================

t1 = time.time()

# default config path
logger.info("Setting up disease configuration")
config_path = os.path.join(os.path.dirname(__file__), "../june/configs/config_simulation.yaml")
logger.info(f"Using config from: {config_path}")

disease_name = "covid19"
try:
    disease_config = DiseaseConfig(disease_name)
    GlobalContext.set_disease_config(disease_config)
    logger.info(f"Successfully loaded disease configuration for {disease_name}")
except Exception as e:
    logger.error(f"Failed to load disease configuration: {e}")
    raise

try:
    logger.info("Loading geography and boundaries from files...")
    geography = Geography.from_file({"super_area": msoas_to_load})
    logger.info(f"Successfully loaded geography with {len(geography.areas)} areas and {len(geography.super_areas)} super areas")
    
    """ # Initialize airports with proper error handling and data validation
    try:
        # First check if required airport data exists
        airport_data_file = data_path / "input/geography/uk_airports.csv"
        if not airport_data_file.exists():
            logger.error("Airport data file not found. Creating template file...")
            with open(airport_data_file, 'w') as f:
                f.write("name,latitude,longitude,passengers_per_year\n")
                # Add sample data or leave empty for user to fill
            raise FileNotFoundError(f"Please populate airport data at: {airport_data_file}")

        # Initialize airports
        geography.airports = Airports.for_geography(
            geography=geography,
            data_file=airport_data_file,
            config_file=configs_path / "defaults/geography/airports.yaml"
        )
        if geography.airports:
            logger.info(f"Added {len(geography.airports.members)} airports")
            # Log sample of created airports
            for airport in list(geography.airports.members)[:3]:
                logger.info(f"Airport: {airport.name}, Capacity: {airport.capacity}")
        else:
            logger.warning("No airports created - check airport data and config")
            
    except FileNotFoundError as e:
        logger.error(f"Airport data not found: {e}")
        geography.airports = None
    except Exception as e:
        logger.warning(f"Failed to add airports: {e}")
        geography.airports = None """

    try:
        geography.hospitals = Hospitals.for_geography(geography)
        logger.info(f"Added {len(geography.hospitals) if geography.hospitals else 0} hospitals")
    except Exception as e:
        logger.warning(f"Failed to add hospitals: {e}")
        geography.hospitals = None
    
    try:
        geography.companies = Companies.for_geography(geography)
        logger.info(f"Added {len(geography.companies) if geography.companies else 0} companies")
    except Exception as e:
        logger.warning(f"Failed to add companies: {e}")
        geography.companies = None
    
    try:
        geography.schools = Schools.for_geography(geography)
        logger.info(f"Added {len(geography.schools) if geography.schools else 0} schools")
    except Exception as e:
        logger.warning(f"Failed to add schools: {e}")
        geography.schools = None
    
    try:
        geography.universities = Universities.for_geography(geography)
        logger.info(f"Added {len(geography.universities) if geography.universities else 0} universities")
    except Exception as e:
        logger.warning(f"Failed to add universities: {e}")
        geography.universities = None
    
    try:
        geography.care_homes = CareHomes.for_geography(geography)
        logger.info(f"Added {len(geography.care_homes) if geography.care_homes else 0} care homes")
    except Exception as e:
        logger.warning(f"Failed to add care homes: {e}")
        geography.care_homes = None

except Exception as e:
    logger.error(f"Failed to create geography: {e}")
    raise

try:
    world = generate_world_from_geography(geography, include_households=True)
    print("World successfully generated from geography.")
    
    # Aircraft fleet will be automatically initialized if airports exist
    if hasattr(world, 'aircrafts') and world.aircrafts:
        logger.info(f"Created aircraft fleet with {len(world.aircrafts)} aircraft")
    
except Exception as e:
    print(f"Error generating world from geography: {e}")
    raise

try:
    # Initialise leisure venues if they don't exist
    world.pubs = Pubs.for_geography(geography)
    world.cinemas = Cinemas.for_geography(geography)
    world.groceries = Groceries.for_geography(geography)
    world.gyms = Gyms.for_geography(geography)
    
    # Generate and distribute leisure activities
    leisure = generate_leisure_for_config(world)
    leisure.distribute_social_venues_to_areas(
        areas=world.areas, super_areas=world.super_areas
    )  # this assigns possible social venues to people.
    print("Leisure activities successfully added to world.")
except Exception as e:
    print(f"Warning: Error adding leisure activities: {e}")
    print("Continuing without complete leisure facilities.")

try:
    travel = Travel()
    travel.initialise_commute(world)
    print("Travel and commuting successfully initialised.")
except Exception as e:
    print(f"Warning: Error initialising travel and commuting: {e}")
    print("Continuing without complete travel functionality.")


t2 = time.time()
runtime = t2 - t1
logger.info(f"World creation completed in {runtime:.2f} seconds")

try:
    logger.info("Saving world to HDF5 file...")
    world.to_hdf5("tests.hdf5")
    logger.info("World successfully saved to tests.hdf5")
    logger.info("World creation process completed successfully")
    logger.info("Done :)")

except Exception as e:
    logger.error(f"Error saving world to HDF5: {e}")
    logger.warning("World creation completed but saving failed.")


try:
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumulative')
    profile_filename = 'simulation_profile.stats'
    stats.dump_stats(profile_filename)
    logger.info(f"Performance profiling data saved to {profile_filename}")
except Exception as e:
    logger.error(f"Failed to save profiling data: {e}")
    
logger.info("Script execution completed")

