import time
import numpy as np
import numba as nb
import random
from pathlib import Path
from mpi4py import MPI
import h5py
import sys
import cProfile
import sys

from june.hdf5_savers import generate_world_from_hdf5, load_population_from_hdf5
from june.interaction import Interaction
from june.infection import Infection, InfectionSelector, HealthIndexGenerator
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
from june.groups.travel import Travel
from june.groups.leisure import Cinemas, Pubs, Groceries, generate_leisure_for_config
from june.simulator import Simulator
from june.infection_seed import InfectionSeed, Observed2Cases
from june.policy import Policies
from june import paths
from june.groups.commute import *
from june.logger import Logger
from june.logger.read_logger import ReadLogger
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


# a decorator for profiling
def profile(filename=None, comm=MPI.COMM_WORLD):
  def prof_decorator(f):
    def wrap_f(*args, **kwargs):
      pr = cProfile.Profile()
      pr.enable()
      result = f(*args, **kwargs)
      pr.disable()

      if filename is None:
        pr.print_stats()
      else:
        filename_r = filename + ".{}".format(comm.rank)
        pr.dump_stats(filename_r)

      return result
    return wrap_f
  return prof_decorator


if len(sys.argv) == 2:
    checkpoint_path = sys.argv[1]
    seed = 999
elif len(sys.argv) == 3:
    checkpoint_path = sys.argv[1]
    seed = int(sys.argv[2])
else:
    raise ValueError("Provide path to checkpoint usage is python run_parallel_simulation.py path/to/checkpoint random_seed(optional)")
set_random_seed(seed)

world_file = f"./tests.hdf5"
config_path = "./config_simulation.yaml"

# parallel setup

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()
if seed == 999:
    save_path = "results_from_checkpoint"
else:
    save_path = f"results_from_checkpoint_{seed:02d}"

def generate_simulator():
    with h5py.File(world_file, "r") as f:
        n_super_areas = f["geography"].attrs["n_super_areas"]
    
    
    logger = Logger(save_path = save_path, file_name=f"logger.{rank}.hdf5")
    
    super_areas_to_domain_dict = generate_super_areas_to_domain_dict(n_super_areas, size)
    
    domain = Domain.from_hdf5(
        domain_id=rank,
        super_areas_to_domain_dict=super_areas_to_domain_dict,
        hdf5_file_path=world_file,
    )
    logger.log_population(domain.people)
    #
    # regenerate lesiure
    leisure = generate_leisure_for_config(domain, config_path)
    #
    # health index and infection selecctor
    health_index_generator = HealthIndexGenerator.from_file(asymptomatic_ratio=0.39)
    infection_selector = InfectionSelector.from_file(
        health_index_generator=health_index_generator
    )
    oc = Observed2Cases.from_file(
            health_index_generator=health_index_generator,
            smoothing=True
            )
    daily_cases_per_region = oc.get_regional_latent_cases()
    daily_cases_per_super_area = oc.convert_regional_cases_to_super_area(
            daily_cases_per_region,
            dates=['2020-02-28', '2020-03-02']
            )
    infection_seed = InfectionSeed(world=domain,
            infection_selector=infection_selector,
            daily_super_area_cases=daily_cases_per_super_area,
            seed_strength=0.66,
            )
    # interaction
    interaction = Interaction.from_file()
    
    # policies
    policies = Policies.from_file()
    
    # create simulator
    
    travel = Travel()
    simulator = Simulator.from_checkpoint(
        world=domain,
        checkpoint_path=checkpoint_path,
        policies=policies,
        interaction=interaction,
        leisure=leisure,
        travel=travel,
        infection_selector=infection_selector,
        infection_seed=infection_seed,
        config_filename=config_path,
        logger=logger,
    )
    print("simulator ready to go")
    return simulator

def run_simulator(simulator):

    t1 = time.time()
    simulator.run()
    t2 = time.time()
    print(f" Simulation took {t2-t1} seconds")

def save_summary():
    if rank == 0:
        logger = ReadLogger(save_path, n_processes=size)
        logger.world_summary().to_csv(Path(save_path) / "summary.csv")

if __name__ == "__main__":
    simulator = generate_simulator()
    run_simulator(simulator)
    save_summary()
