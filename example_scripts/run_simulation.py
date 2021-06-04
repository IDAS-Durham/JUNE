import time
import numpy as np
import numba as nb
import random
import json
from pathlib import Path
from mpi4py import MPI
import h5py
import sys
import cProfile

from june.hdf5_savers import generate_world_from_hdf5, load_population_from_hdf5
from june.interaction import Interaction
from june.epidemiology.infection import (
    Infection,
    InfectionSelector,
    InfectionSelectors,
    HealthIndexGenerator,
    SymptomTag,
    SusceptibilitySetter,
    Covid19,
    B16172
)
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
from june.groups.travel import Travel
from june.groups.leisure import Cinemas, Pubs, Groceries, generate_leisure_for_config
from june.simulator import Simulator
from june.epidemiology.epidemiology import Epidemiology
from june.epidemiology.infection_seed import InfectionSeed, Observed2Cases, InfectionSeeds
from june.policy import Policies
from june.event import Events
from june import paths
from june.records import Record
from june.records.records_writer import combine_records
from june.domains import Domain, DomainSplitter
from june.mpi_setup import mpi_comm, mpi_rank, mpi_size


def keys_to_int(x):
    return {int(k): v for k, v in x.items()}


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

world_file = f"./tests.hdf5"
config_path = "./config_simulation.yaml"

if seed == 999:
    save_path = "results"
else:
    save_path = f"results_{seed:02d}"


def generate_simulator():
    record = Record(record_path=save_path, record_static_data=True, mpi_rank=mpi_rank)
    if mpi_rank == 0:
        with h5py.File(world_file, "r") as f:
            super_area_ids = f["geography"]["super_area_id"]
            super_area_names = f["geography"]["super_area_name"]
            super_area_name_to_id = {
                name.decode(): id for name, id in zip(super_area_names, super_area_ids)
            }
        super_areas_per_domain, score_per_domain = DomainSplitter.generate_world_split(
            number_of_domains=mpi_size, world_path=world_file
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
    mpi_comm.Barrier()
    if mpi_rank > 0:
        with open("super_area_ids_to_domain.json", "r") as f:
            super_area_ids_to_domain_dict = json.load(f, object_hook=keys_to_int)
    domain = Domain.from_hdf5(
        domain_id=mpi_rank,
        super_areas_to_domain_dict=super_area_ids_to_domain_dict,
        hdf5_file_path=world_file,
    )
    record.static_data(world=domain)
    # regenerate lesiure
    leisure = generate_leisure_for_config(domain, config_path)
    #
    # health index and infection selecctor
    health_index_generator = HealthIndexGenerator.from_file()
    selector_c19 = InfectionSelector(
        infection_class=Covid19,
        health_index_generator=health_index_generator
    )
    selector_indian = InfectionSelector(
        infection_class=B16172,
        health_index_generator=health_index_generator
    )
    inf_selectors = InfectionSelectors([selector_c19, selector_indian])
    oc = Observed2Cases.from_file(
        health_index_generator=health_index_generator, smoothing=True
    )
    daily_cases_per_region = oc.get_regional_latent_cases()
    daily_cases_per_super_area = oc.convert_regional_cases_to_super_area(
        daily_cases_per_region,
        starting_date="2020-02-28",
    )
    infection_seed = InfectionSeed(
        world=domain,
        infection_selector=selector_c19,
        daily_super_area_cases=daily_cases_per_super_area,
        seed_strength=100,
    )
    #susceptibility_setter = SusceptibilitySetter()

    epidemiology = Epidemiology(
        infection_selectors=inf_selectors,
        infection_seeds=InfectionSeeds([infection_seed]),
        #susceptibility_setter=susceptibility_setter,
    )

    # interaction
    interaction = Interaction.from_file(
        config_filename="./config_interaction.yaml"
    )
    # policies
    policies = Policies.from_file()

    # events
    events = Events.from_file()

    # create simulator

    travel = Travel()
    simulator = Simulator.from_file(
        world=domain,
        policies=policies,
        events=events,
        interaction=interaction,
        leisure=leisure,
        travel=travel,
        epidemiology=epidemiology,
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
    mpi_comm.Barrier()
    if mpi_rank == 0:
        combine_records(save_path)
