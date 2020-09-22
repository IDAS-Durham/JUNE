from june.world import World
from june.demography.geography import Geography
from june.demography import Demography
from june.groups import (
    Hospitals,
    Schools,
    Companies,
    Households,
    CareHomes,
    Cemeteries,
    Universities,
)
from june.groups.leisure import Pubs, Cinemas, Groceries, generate_leisure_for_config
from june.world import generate_world_from_geography
import pickle
import sys
import time
import numpy as np

# load london super areas
london_areas = np.loadtxt("./london_areas.txt", dtype=np.str_)

t1 = time.time()

# default config path
config_path = "./config_simulation.yaml"

# define geography, let's run the first 20 super areas of london
geography = Geography.from_file({"super_area": london_areas[40:60]})

# add buildings
geography.hospitals = Hospitals.for_geography(geography)
geography.companies = Companies.for_geography(geography)
geography.schools = Schools.for_geography(geography)
geography.universities = Universities.for_super_areas(geography.super_areas)
geography.care_homes = CareHomes.for_geography(geography)
## generate world
world = generate_world_from_geography(
    geography, include_households=True, include_commute=True
)
#
## some leisure activities
world.pubs = Pubs.for_geography(geography)
world.cinemas = Cinemas.for_geography(geography)
world.groceries = Groceries.for_geography(geography)
leisure = generate_leisure_for_config(world, config_filename=config_path)
leisure.distribute_social_venues_to_households(
    world.households, super_areas=world.super_areas
)  # this assigns possible social venues to people.
t2 = time.time()
print(f"Took {t2 -t1} seconds to run.")
# save the world to hdf5 to load it later
world.to_hdf5("serial_world.hdf5")
print("Done :)")
