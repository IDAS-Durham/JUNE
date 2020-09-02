import time
import numpy as np
import numba as nb
import random

from june.hdf5_savers import generate_world_from_hdf5, load_population_from_hdf5
from june.demography.geography import Geography
from june.interaction import Interaction
from june.infection import Infection, InfectionSelector, HealthIndexGenerator
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
from june.groups.leisure import Cinemas, Pubs, Groceries, generate_leisure_for_config
from june.simulator import Simulator
from june.infection_seed import InfectionSeed
from june.policy import Policies
from june.logger import Logger
from june import paths
from june.groups.commute import *


def set_random_seed(seed=999):
    """
    Sets global seeds for testing in numpy, random, and numbaized numpy.
    """

    @nb.njit(cache=True)
    def set_seed_numba(seed):
        return np.random.seed(seed)

    np.random.seed(seed)
    set_seed_numba(seed)
    random.seed(seed)
    return


set_random_seed()

world_file = "./london_50.hdf5"
config_path = "./config_nocommute.yaml"

world = generate_world_from_hdf5(world_file, chunk_size=1_000_000)
print("World loaded succesfully")

logger = Logger(save_path='results_nompi', file_name=f'logger_0.hdf5') 
population = load_population_from_hdf5(world_file)
logger.log_population(population)


# regenerate lesiure
leisure = generate_leisure_for_config(world, config_path)
#
# health index and infection selecctor
health_index_generator = HealthIndexGenerator.from_file(asymptomatic_ratio=0.2)
infection_selector = InfectionSelector.from_file(health_index_generator=health_index_generator)

# interaction
interaction = Interaction.from_file()

# initial infection seeding
infection_seed = InfectionSeed(
   world.super_areas, infection_selector,
)

infection_seed.unleash_virus(50) # number of initial cases

# policies
policies = Policies.from_file()

# create simulator

simulator = Simulator.from_file(
   world=world,
   policies=policies,
   interaction=interaction,
   leisure=leisure,
   infection_selector=infection_selector,
   config_filename=config_path,
   logger=logger,
)
print("simulator ready to go")

t1 = time.time()
simulator.run()
t2 = time.time()

print(f" Simulation took {t2-t1} seconds")

