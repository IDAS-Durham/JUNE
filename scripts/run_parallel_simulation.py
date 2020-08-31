import time
import numpy as np
import numba as nb
import random
from mpi4py import MPI
import h5py

from june.hdf5_savers import generate_world_from_hdf5
from june.demography.geography import Geography
from june.interaction import Interaction
from june.infection import Infection, InfectionSelector, HealthIndexGenerator
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
from june.groups.leisure import Cinemas, Pubs, Groceries, generate_leisure_for_config
from june.simulator import Simulator
from june.infection_seed import InfectionSeed
from june.policy import Policies
from june import paths
from june.groups.commute import *
from june.domain import Domain, generate_super_areas_to_domain_dict


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

world_file = "./../../june_scripts/NEY_simple.hdf5"
config_path = "./config_basic.yaml"

# parallel setup

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

with h5py.File(world_file, "r") as f:
    print(f["geography"].keys())
    n_super_areas = f["geography"].attrs["n_super_areas"]


#london_areas = np.loadtxt("./london_areas.txt", dtype=np.str_)[40:60]
super_areas_to_domain_dict = generate_super_areas_to_domain_dict(
    n_super_areas, size
)
print("MPI SIZE", size)
domain = Domain.from_hdf5(
    domain_id=rank,
    super_areas_to_domain_dict=super_areas_to_domain_dict,
    hdf5_file_path=world_file
)
#
# regenerate lesiure
#leisure = generate_leisure_for_config(domain, config_path)
leisure = None
#
# health index and infection selecctor
health_index_generator = HealthIndexGenerator.from_file(asymptomatic_ratio=0.2)
infection_selector = InfectionSelector.from_file(
    health_index_generator=health_index_generator
)

# interaction
interaction = Interaction.from_file()

# initial infection seeding
infection_seed = InfectionSeed(domain.super_areas, infection_selector,)

infection_seed.unleash_virus(50)  # number of initial cases

# policies
policies = Policies.from_file()

# create simulator

simulator = Simulator.from_file(
    world=domain,
    policies=policies,
    interaction=interaction,
    leisure=leisure,
    infection_selector=infection_selector,
    config_filename=config_path,
    save_path=f"results_{rank}",
)
print("simulator ready to go")

t1 = time.time()
simulator.run()
t2 = time.time()

print(f" Simulation took {t2-t1} seconds")
