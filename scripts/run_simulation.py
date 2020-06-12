import time

from june.world import generate_world_from_hdf5
from june.hdf5_savers import load_geography_from_hdf5
from june.demography.geography import Geography
from june.interaction import ContactAveraging
from june.infection import Infection
from june.infection.symptoms import SymptomsConstant
from june.infection.transmission import TransmissionConstant
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
from june.groups.leisure import Cinemas, Pubs, Groceries
from june.simulator import Simulator
from june.seed import Seed
from june import paths
from june.infection.infection import InfectionSelector
from june.groups.commute import *

world_file = "world.hdf5"

world = generate_world_from_hdf5(world_file, chunk_size=1_000_000)
print("World loaded succesfully")
geography = load_geography_from_hdf5(world_file)

world.pubs = Pubs.for_geography(geography)
world.cinemas = Cinemas.for_geography(geography)
world.groceries = Groceries.for_super_areas(geography.super_areas)
print("leisure good")

#cemeteries
world.cemeteries = Cemeteries()

# commute
world.initialise_commuting()
print("commute OK")
######

# interaction
# select path to infection configuration
selector = InfectionSelector.from_file()
interaction = ContactAveraging.from_file(selector=selector)

print("interaction OK")

# initial infection seeding
seed = Seed.from_file(super_areas=world.super_areas, 
        selector=selector,)
# two options, randomly, or one specific area.

# 1. specific area
#seed_area = "E02000001" # area to start seed
#for super_area in world.super_areas:
#    if super_area.name == seed_area:
#        print("super area found")
#        break
#seed.infect_super_area(super_area, 99) # seed 99 infections in seed_area

# 2. randomly distribute
# this will put 500 infected randomly

print("seeding OK")

# path to main simulation config file
CONFIG_PATH = "../configs/config_example.yaml"

simulator = Simulator.from_file(
    world,
    interaction,
    selector,
    seed=seed,
    config_filename=CONFIG_PATH,
    save_path="results",
)
print("simulator ready to go")

t1 = time.time()
simulator.run()
t2 = time.time()

print(f" Simulation took {t2-t1} seconds")

