import h5py
import numpy as np
from typing import List
from june.global_context import GlobalContext
from june.groups.group.make_subgroups import SubgroupParams

from .utils import read_dataset
from june.groups.leisure import (
    Pub,
    Pubs,
    Grocery,
    Groceries,
    Cinema,
    Cinemas,
    Gym,
    Gyms,
    SocialVenues,
)
from june.world import World

nan_integer = -999


def save_social_venues_to_hdf5(social_venues_list: List[SocialVenues], file_path: str):
    with h5py.File(file_path, "a") as f:
        f.create_group("social_venues")
        for social_venues in social_venues_list:
            n_svs = len(social_venues)
            social_venues_dset = f["social_venues"].create_group(social_venues.spec)
            ids = []
            coordinates = []
            areas = []
            for sv in social_venues:
                ids.append(sv.id)
                coordinates.append(np.array(sv.coordinates, dtype=np.float64))
                if sv.super_area is None:
                    areas.append(nan_integer)
                else:
                    areas.append(sv.area.id)
            ids = np.array(ids, dtype=np.int64)
            coordinates = np.array(coordinates, dtype=np.float64)
            areas = np.array(areas, dtype=np.int64)
            social_venues_dset.attrs["n"] = n_svs
            social_venues_dset.create_dataset("id", data=ids)
            social_venues_dset.create_dataset("coordinates", data=coordinates)
            social_venues_dset.create_dataset("area", data=areas)


def load_social_venues_from_hdf5(
    file_path: str, domain_areas=None, config_filename=None
):
    social_venues_dict = {}

    disease_config = GlobalContext.get_disease_config()

    Pub_Class = Pub
    Pub_Class.subgroup_params = SubgroupParams.from_disease_config(disease_config)

    Cinema_Class = Cinema
    Cinema_Class.subgroup_params = SubgroupParams.from_disease_config(disease_config)

    Grocery_Class = Grocery
    Grocery_Class.subgroup_params = SubgroupParams.from_disease_config(disease_config)

    Gym_Class = Gym
    Gym_Class.subgroup_params = SubgroupParams.from_disease_config(disease_config)

    spec_to_group_dict = {
        "pubs": Pub_Class,
        "cinemas": Cinema_Class,
        "groceries": Grocery_Class,
        "gyms": Gym_Class,
    }
    spec_to_supergroup_dict = {
        "pubs": Pubs,
        "cinemas": Cinemas,
        "groceries": Groceries,
        "gyms": Gyms,
    }

    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        for spec in f["social_venues"]:
            data = f["social_venues"][spec]
            social_venues = []
            n = data.attrs["n"]
            if n == 0:
                social_venues_dict[spec] = None
                continue
            ids = read_dataset(data["id"])
            coordinates = read_dataset(data["coordinates"])
            areas = read_dataset(data["area"])
            for k in range(n):
                if domain_areas is not None:
                    area = areas[k]
                    if area == nan_integer:
                        raise ValueError(
                            "if ``domain_areas`` is True, I expect not Nones super areas."
                        )
                    if area not in domain_areas:
                        continue
                social_venue = spec_to_group_dict[spec]()
                social_venue.id = ids[k]
                social_venue.coordinates = coordinates[k]
                social_venues.append(social_venue)
            social_venues_dict[spec] = spec_to_supergroup_dict[spec](social_venues)
        return social_venues_dict


def restore_social_venues_properties_from_hdf5(
    world: World, file_path: str, domain_areas=None
):
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        for spec in f["social_venues"]:
            data = f["social_venues"][spec]
            n = data.attrs["n"]
            if n == 0:
                continue
            social_venues = getattr(world, spec)
            ids = read_dataset(data["id"])
            areas = read_dataset(data["area"])
            for k in range(n):
                if domain_areas is not None:
                    area = areas[k]
                    if area == nan_integer:
                        raise ValueError(
                            "if ``domain_areas`` is True, I expect not Nones super areas."
                        )
                    if area not in domain_areas:
                        continue
                social_venue = social_venues.get_from_id(ids[k])
                area = areas[k]
                if area == nan_integer:
                    area = None
                else:
                    area = world.areas.get_from_id(area)
                social_venue.area = area
