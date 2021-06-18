from typing import Optional, List
import numpy as np
from datetime import datetime, timedelta
import h5py
from collections import defaultdict
from glob import glob
import logging

from june.world import World
from june.interaction import Interaction
from june.groups.leisure import Leisure
from june.policy import Policies
from june.event import Events
from june import paths
from june.simulator import Simulator
from june.mpi_setup import mpi_comm, mpi_size, mpi_rank
from june.epidemiology.epidemiology import Epidemiology
from june.epidemiology.infection import (
    Transmission,
    TransmissionGamma,
    TransmissionXNExp,
    InfectionSelectors,
    Infection,
)
from june.epidemiology.infection_seed import InfectionSeeds
from june.hdf5_savers.utils import read_dataset, write_dataset
from june.demography import Population
from june.demography.person import Activities, Person
from june.hdf5_savers import (
    save_infections_to_hdf5,
    load_infections_from_hdf5,
    save_immunities_to_hdf5,
    load_immunities_from_hdf5,
)
from june.groups.travel import Travel
import june.simulator as june_simulator_module

default_config_filename = june_simulator_module.default_config_filename

logger = logging.getLogger("checkpoint_saver")


def save_checkpoint_to_hdf5(
    population: Population, date: str, hdf5_file_path: str, chunk_size: int = 50000
):
    """
    Saves a checkpoint at the given date by saving the infection information of the world.

    Parameters
    ----------
    population:
        world's population
    date:
        date of the checkpoint
    hdf5_file_path
        path where to save the hdf5 checkpoint
    chunk_size
        hdf5 chunk_size to write data
    """
    dead_people_ids = [person.id for person in population if person.dead]
    people_ids = []
    infected_people_ids = []
    infection_list = []
    for person in population:
        people_ids.append(person.id)
        if person.infected:
            infected_people_ids.append(person.id)
            infection_list.append(person.infection)
    with h5py.File(hdf5_file_path, "w") as f:
        f.create_group("time")
        f["time"].attrs["date"] = date
        f.create_group("people_data")
        for name, data in zip(
            ["people_id", "infected_id", "dead_id"],
            [
                people_ids,
                infected_people_ids,
                dead_people_ids,
            ],
        ):
            write_dataset(
                group=f["people_data"],
                dataset_name=name,
                data=np.array(data, dtype=np.int64),
            )
    save_infections_to_hdf5(
        hdf5_file_path=hdf5_file_path,
        infections=infection_list,
        chunk_size=chunk_size,
    )
    immunities = [person.immunity for person in population]
    save_immunities_to_hdf5(hdf5_file_path=hdf5_file_path, immunities=immunities)


def load_checkpoint_from_hdf5(hdf5_file_path: str, chunk_size=50000, load_date=True):
    """
    Loads checkpoint data from hdf5.

    Parameters
    ----------
    hdf5_file_path
        hdf5 path to load from
    chunk_size
        number of hdf5 chunks to use while loading
    """
    ret = {}
    ret["infection_list"] = load_infections_from_hdf5(
        hdf5_file_path, chunk_size=chunk_size
    )
    ret["immunity_list"] = load_immunities_from_hdf5(
        hdf5_file_path, chunk_size=chunk_size
    )
    with h5py.File(hdf5_file_path, "r") as f:
        people_group = f["people_data"]
        ret["infected_id"] = people_group["infected_id"][:]
        ret["dead_id"] = people_group["dead_id"][:]
        ret["people_id"] = people_group["people_id"][:]
        if load_date:
            ret["date"] = f["time"].attrs["date"]
    return ret


def combine_checkpoints_for_ranks(hdf5_file_root: str):
    """
    After running a parallel simulation with checkpoints, the
    checkpoint data will be scattered accross, with each process
    saving a checkpoint_date.0.hdf5 file. This function can be used
    to unify all data in one single checkpoint, so that we can load it
    later with any arbitray number of cores.

    Parameters
    ----------
    hdf5_file_root
        the str root of the pasts like "checkpoint_2020-01-01". The checkpoint files
        will be expected to have names like "checkpoint_2020-01-01.{rank}.hdf5 where
        rank = 0, 1, 2, etc.
    """
    checkpoint_files = glob(hdf5_file_root + ".[0-9]*.hdf5")
    try:
        cp_date = hdf5_file_root.split("_")[-1]
    except:
        cp_date = hdf5_file_root
    logger.info(f"found {len(checkpoint_files)} {cp_date} checkpoint files")
    ret = load_checkpoint_from_hdf5(checkpoint_files[0])
    for i in range(1, len(checkpoint_files)):
        file = checkpoint_files[i]
        ret2 = load_checkpoint_from_hdf5(file, load_date=False)
        for key, value in ret2.items():
            ret[key] = np.concatenate((ret[key], value))

    unified_checkpoint_path = hdf5_file_root + ".hdf5"
    with h5py.File(unified_checkpoint_path, "w") as f:
        f.create_group("time")
        f["time"].attrs["date"] = ret["date"]
        f.create_group("people_data")
        for name in ["people_id", "infected_id", "dead_id"]:
            write_dataset(
                group=f["people_data"],
                dataset_name=name,
                data=np.array(ret[name], dtype=np.int64),
            )
    save_infections_to_hdf5(
        hdf5_file_path=unified_checkpoint_path,
        infections=ret["infection_list"],
        chunk_size=1000000,
    )
    save_immunities_to_hdf5(
        hdf5_file_path=unified_checkpoint_path,
        immunities=ret["immunity_list"],
    )


def restore_simulator_to_checkpoint(
    simulator,
    world: World,
    checkpoint_path: str,
    chunk_size: Optional[int] = 50000,
    reset_infections=False,
):
    """
    Initializes the simulator from a saved checkpoint. The arguments are the same as the standard .from_file()
    initialisation but with the additional path to where the checkpoint pickle file is located.
    The checkpoint saves information about the infection status of all the people in the world as well as the timings.
    Note, nonetheless, that all the past infections / deaths will have the checkpoint date as date.

    Parameters
    ----------
    simulator:
        An instance of the Simulator class
    checkpoint_path:
        path to the hdf5 file containing the checkpoint data
    chunk_size
        chunk load size of the hdf5
    reset_infected
        whether to reset the current infected to 0. Useful for reseeding.
    """
    people_ids = set(world.people.people_ids)
    checkpoint_data = load_checkpoint_from_hdf5(checkpoint_path, chunk_size=chunk_size)
    for dead_id in checkpoint_data["dead_id"]:
        if dead_id not in people_ids:
            continue
        person = simulator.world.people.get_from_id(dead_id)
        person.dead = True
        cemetery = world.cemeteries.get_nearest(person)
        cemetery.add(person)
        person.subgroups = Activities(None, None, None, None, None, None)
    if not reset_infections:
        for infected_id, infection in zip(
            checkpoint_data["infected_id"], checkpoint_data["infection_list"]
        ):
            if infected_id not in people_ids:
                continue
            person = simulator.world.people.get_from_id(infected_id)
            person.infection = infection
    # restore immunities
    for person_id, immunity in zip(
        checkpoint_data["people_id"], checkpoint_data["immunity_list"]
    ):
        person = world.people.get_from_id(person_id)
        person.immunity = immunity
    # restore timer
    checkpoint_date = datetime.strptime(checkpoint_data["date"], "%Y-%m-%d")
    # we need to start the next day
    checkpoint_date += timedelta(days=1)
    simulator.timer.reset_to_new_date(checkpoint_date)
    return simulator


def generate_simulator_from_checkpoint(
    world: World,
    checkpoint_path: str,
    interaction: Interaction,
    chunk_size: Optional[int] = 50000,
    epidemiology: Optional[Epidemiology] = None,
    policies: Optional[Policies] = None,
    leisure: Optional[Leisure] = None,
    travel: Optional[Travel] = None,
    events: Optional[Events] = None,
    config_filename: str = default_config_filename,
    record: "Record" = None,
    reset_infections=False,
):
    simulator = Simulator.from_file(
        world=world,
        interaction=interaction,
        epidemiology=epidemiology,
        policies=policies,
        leisure=leisure,
        travel=travel,
        events=events,
        config_filename=config_filename,
        record=record,
    )
    return restore_simulator_to_checkpoint(
        world=world,
        checkpoint_path=checkpoint_path,
        chunk_size=chunk_size,
        simulator=simulator,
        reset_infections=reset_infections,
    )
