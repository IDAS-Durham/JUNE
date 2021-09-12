import h5py
import numpy as np
from collections import defaultdict
from june.world import World

from .utils import read_dataset


def get_commuters_per_super_area(world: World):
    ret = defaultdict(int)
    if world.stations:
        for station in world.stations:
            ret[station.super_area.name] += len(station.commuter_ids)
    if world.cities:
        for city in world.cities:
            n_internal_commuters = len(city.internal_commuter_ids)
            if n_internal_commuters == 0:
                continue
            city_stations = city.city_stations
            n_stations = len(city_stations)
            n_commuters_per_station = n_internal_commuters / n_stations
            for station in city_stations:
                ret[station.super_area.name] += n_commuters_per_station
    return ret


def save_data_for_domain_decomposition(world: World, file_path: str):
    """
    Saves data required to generate a domain decomposition. For each super area,
    we save:
        - Population
        - Number of workers
        - Number of pupils
        - Number of commuters
    """
    super_area_names = []
    super_area_population = []
    super_area_pupils = []
    super_area_workers = []
    super_area_commuters = []
    commuters_per_super_area = get_commuters_per_super_area(world)
    for super_area in world.super_areas:
        super_area_names.append(super_area.name.encode("ascii", "ignore"))
        super_area_population.append(len(super_area.people))
        super_area_workers.append(len(super_area.workers))
        super_area_pupils.append(
            sum(
                [
                    len(school.people)
                    for area in super_area.areas
                    for school in area.schools
                ]
            )
        )
        super_area_commuters.append(commuters_per_super_area[super_area.name])
    super_area_names = np.array(super_area_names, dtype="S20")
    super_area_population = np.array(super_area_population, dtype=np.int64)
    super_area_workers = np.array(super_area_workers, dtype=np.int64)
    super_area_commuters = np.array(super_area_commuters, dtype=np.int64)
    super_area_pupils = np.array(super_area_pupils, dtype=np.int64)
    with h5py.File(file_path, "a") as f:
        group = f.create_group("domain_decomposition_data")
        group.create_dataset("super_area_names", data=super_area_names)
        group.create_dataset("super_area_population", data=super_area_population)
        group.create_dataset("super_area_workers", data=super_area_workers)
        group.create_dataset("super_area_pupils", data=super_area_pupils)
        group.create_dataset("super_area_commuters", data=super_area_commuters)


def load_data_for_domain_decomposition(file_path: str):
    """
    Reads the saved data for the domain decomposition.
    See the docs of read_data_for_domain_decomposition for more information.
    """
    ret = {}
    with h5py.File(file_path, "r") as f:
        data = f["domain_decomposition_data"]
        super_area_names = read_dataset(data["super_area_names"])
        super_area_population = read_dataset(data["super_area_population"])
        super_area_workers = read_dataset(data["super_area_workers"])
        super_area_pupils = read_dataset(data["super_area_pupils"])
        super_area_commuters = read_dataset(data["super_area_commuters"])
        for i in range(len(super_area_names)):
            super_area_name = super_area_names[i].decode()
            sa_dict = {}
            sa_dict["n_people"] = super_area_population[i]
            sa_dict["n_workers"] = super_area_workers[i]
            sa_dict["n_pupils"] = super_area_pupils[i]
            sa_dict["n_commuters"] = super_area_commuters[i]
            ret[super_area_name] = sa_dict
    return ret
