import time
import numpy as np
import numba as nb
import random
from mpi4py import MPI
import h5py
import sys

from june.hdf5_savers import generate_world_from_hdf5, load_population_from_hdf5
from june.interaction import Interaction
from june.infection import Infection, InfectionSelector, HealthIndexGenerator
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
from june.groups.travel import Travel
from june.groups.leisure import Cinemas, Pubs, Groceries, generate_leisure_for_config
from june.simulator import Simulator
from june.infection_seed import InfectionSeed
from june.policy import Policies
from june import paths
from june.groups.commute import *
from june.logger import Logger
from june.domain import Domain, generate_super_areas_to_domain_dict


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


if len(sys.argv) > 1:
    seed = int(sys.argv[1])
else:
    seed = 999
set_random_seed(seed)

world_file = "./london_parallel_60.hdf5"
config_path = "./config_nocommute.yaml"

# parallel setup

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

with h5py.File(world_file, "r") as f:
    n_super_areas = f["geography"].attrs["n_super_areas"]

# log_population
if seed == 999:
    save_path = "results"
else:
    save_path = f"results_{seed:02d}"
logger = Logger(save_path = save_path, file_name=f"logger.{rank}.hdf5")
population = load_population_from_hdf5(world_file)
logger.log_population(population)

super_areas_to_domain_dict = generate_super_areas_to_domain_dict(n_super_areas, size)
print("MPI SIZE", size)
domain = Domain.from_hdf5(
    domain_id=rank,
    super_areas_to_domain_dict=super_areas_to_domain_dict,
    hdf5_file_path=world_file,
)
#
# regenerate lesiure
leisure = generate_leisure_for_config(domain, config_path)
#
# health index and infection selecctor
health_index_generator = HealthIndexGenerator.from_file(asymptomatic_ratio=0.2)
infection_selector = InfectionSelector.from_file(
    health_index_generator=health_index_generator
)

# interaction
interaction = Interaction.from_file()

# initial infection seeding
# infection_seed = InfectionSeed(domain.super_areas, infection_selector,)

# infection_seed.unleash_virus(50)  # number of initial cases

# policies
policies = Policies.from_file()

# create simulator

travel = Travel()
simulator = Simulator.from_file(
    world=domain,
    policies=policies,
    interaction=interaction,
    leisure=leisure,
    travel=travel,
    infection_selector=infection_selector,
    config_filename=config_path,
    logger=logger,
)
print("simulator ready to go")

if rank == 0:
    n_cases = 50
    selected_people = np.random.choice(len(population.people), n_cases, replace=False)
    selected_ids = []
    for selected_person in selected_people:
        selected_ids.append(population.people[selected_person].id)
    #print("Original Selected IDS = ", selected_ids)
    for rank_receiving in range(1, size):
        comm.send(selected_ids, dest=rank_receiving, tag=0)

elif rank > 0:
    selected_ids = comm.recv(source=0, tag=0)

print("Received selected IDs = ", selected_ids)
print("Len selected IDs = ", len(selected_ids))

for inf_id in selected_ids:
    if inf_id in domain.people.people_dict:
        person = domain.people.get_from_id(inf_id)
        simulator.infection_selector.infect_person_at_time(person, 0.0)

del population

t1 = time.time()
simulator.run()
t2 = time.time()

print(f" Simulation took {t2-t1} seconds")
