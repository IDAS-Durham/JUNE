import h5py
import numpy as np
from typing import List

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
    SocialVenue,
    SocialVenues,
)
from june.world import World

nan_integer = -999
spec_to_group_dict = {"pubs": Pub, "cinemas": Cinema, "groceries": Grocery, "gyms" : Gym}
spec_to_supergroup_dict = {"pubs": Pubs, "cinemas": Cinemas, "groceries": Groceries, "gyms" : Gyms}


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


def load_social_venues_from_hdf5(file_path: str, domain_areas=None):
    social_venues_dict = {}
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

