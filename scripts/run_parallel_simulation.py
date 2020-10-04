import time
import numpy as np
import numba as nb
import random
from pathlib import Path
from mpi4py import MPI
import h5py
import sys
import cProfile

from june.hdf5_savers import generate_world_from_hdf5, load_population_from_hdf5
from june.interaction import Interaction
from june.infection import Infection, InfectionSelector, HealthIndexGenerator, SymptomTag
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
from june.groups.travel import Travel
from june.groups.leisure import Cinemas, Pubs, Groceries, generate_leisure_for_config
from june.simulator import Simulator
from june.infection_seed import InfectionSeed, Observed2Cases
from june.policy import Policies
from june import paths
from june.groups.commute import *
from june.records import Record
from june.domain import Domain, generate_super_areas_to_domain_dict
from june.mpi_setup import mpi_comm, mpi_rank, mpi_size


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


if len(sys.argv) > 1:
    seed = int(sys.argv[1])
else:
    seed = 999
set_random_seed(seed)

world_file = f"./tests_records.hdf5"
config_path = "./config_simulation.yaml"

# parallel setup

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()
if seed == 999:
    save_path = "results"
else:
    save_path = f"results_{seed:02d}"


def generate_simulator():
    with h5py.File(world_file, "r") as f:
        n_super_areas = f["geography"].attrs["n_super_areas"]

    record = Record(
        record_path="results_records", record_static_data=True, mpi_rank=rank
    )

    super_areas_to_domain_dict = generate_super_areas_to_domain_dict(
        n_super_areas, size
    )

    domain = Domain.from_hdf5(
        domain_id=rank,
        super_areas_to_domain_dict=super_areas_to_domain_dict,
        hdf5_file_path=world_file,
    )
    record.static_data(world=domain)
    for hospital in domain.hospitals:
        print(f"Rank {rank} hospital {hospital.id}")
    # regenerate lesiure
    leisure = generate_leisure_for_config(domain, config_path)
    #
    # health index and infection selecctor
    health_index_generator = HealthIndexGenerator.from_file(asymptomatic_ratio=0.2)
    infection_selector = InfectionSelector.from_file(
        health_index_generator=health_index_generator
    )
    oc = Observed2Cases.from_file(
        health_index_generator=health_index_generator, smoothing=True
    )
    daily_cases_per_region = oc.get_regional_latent_cases()
    daily_cases_per_super_area = oc.convert_regional_cases_to_super_area(
        daily_cases_per_region, dates=["2020-02-28", "2020-03-02"]
    )
    infection_seed = InfectionSeed(
        world=domain,
        infection_selector=infection_selector,
        daily_super_area_cases=daily_cases_per_super_area,
        seed_strength=10,
    )

    # interaction
    interaction = Interaction.from_file(
        config_filename="./config_interaction.yaml", population=domain.people
    )
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
        infection_seed=infection_seed,
        config_filename=config_path,
        record=record,
    )
    print("simulator ready to go")
    return simulator


def run_simulator(simulator):

    t1 = time.time()
    simulator.run()
    t2 = time.time()
    print(f" Simulation took {t2-t1} seconds")



if __name__ == "__main__":
    simulator = generate_simulator()
    run_simulator(simulator)
    simulator.record.combine_outputs()
