import h5py
import numpy as np
import logging
from collections import defaultdict, OrderedDict
from itertools import chain

from june.world import World
from june.groups import Household, Households
from .utils import read_dataset

nan_integer = -999

int_vlen_type = h5py.vlen_dtype(np.dtype("int64"))
str_vlen_type = h5py.vlen_dtype(np.dtype("S20"))
logger = logging.getLogger(__name__)


def save_households_to_hdf5(
    households: Households, file_path: str, chunk_size: int = 50000
):
    """
    Saves the households object to hdf5 format file ``file_path``. Currently for each person,
    the following values are stored:
    - id, n_beds, n_icu_beds, super_area, coordinates

    Parameters
    ----------
    companies 
        population object
    file_path
        path of the saved hdf5 file
    chunk_size
        number of people to save at a time. Note that they have to be copied to be saved,
        so keep the number below 1e6.
    """
    n_households = len(households)
    n_chunks = int(np.ceil(n_households / chunk_size))
    with h5py.File(file_path, "a") as f:
        households_dset = f.create_group("households")
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            ids = []
            areas = []
            super_areas = []
            types = []
            max_sizes = []
            for household in households[idx1:idx2]:
                ids.append(household.id)
                if household.area is None:
                    areas.append(nan_integer)
                    super_areas.append(nan_integer)
                else:
                    areas.append(household.area.id)
                    super_areas.append(household.super_area.id)
                if household.type is None:
                    types.append(" ".encode("ascii", "ignore"))
                else:
                    types.append(household.type.encode("ascii", "ignore"))
                max_sizes.append(household.max_size)

            ids = np.array(ids, dtype=np.int)
            areas = np.array(areas, dtype=np.int)
            super_areas = np.array(super_areas, dtype=np.int)
            types = np.array(types, dtype="S20")
            max_sizes = np.array(max_sizes, dtype=np.float)
            if chunk == 0:
                households_dset.attrs["n_households"] = n_households
                households_dset.create_dataset("id", data=ids, maxshape=(None,))
                households_dset.create_dataset("area", data=areas, maxshape=(None,))
                households_dset.create_dataset(
                    "super_area", data=super_areas, maxshape=(None,)
                )
                households_dset.create_dataset("type", data=types, maxshape=(None,))
                households_dset.create_dataset(
                    "max_size", data=max_sizes, maxshape=(None,)
                )

            else:
                newshape = (households_dset["id"].shape[0] + ids.shape[0],)
                households_dset["id"].resize(newshape)
                households_dset["id"][idx1:idx2] = ids
                households_dset["area"].resize(newshape)
                households_dset["area"][idx1:idx2] = areas
                households_dset["super_area"].resize(newshape)
                households_dset["super_area"][idx1:idx2] = super_areas
                households_dset["type"].resize(newshape)
                households_dset["type"][idx1:idx2] = types
                households_dset["max_size"].resize(newshape)
                households_dset["max_size"][idx1:idx2] = max_sizes

        # I dont know how to chunk these...
        households_to_visit = []
        care_homes_to_visit = []
        for household in households:
            if (
                "household" not in household.residences_to_visit 
                or len(household.residences_to_visit["household"]) == 0
            ):
                households_to_visit.append(np.array([nan_integer], dtype=np.int))
            else:
                households_to_visit.append(
                    np.array(
                        [household.id for household in household.residences_to_visit["household"]],
                        dtype=np.int,
                    )
                )
            if (
                "care_home" not in household.residences_to_visit
                or len(household.residences_to_visit["care_home"]) == 0
            ):
                care_homes_to_visit.append(np.array([nan_integer], dtype=np.int))
            else:
                care_homes_to_visit.append(
                    np.array(
                        [care_home.id for care_home in household.residences_to_visit["care_home"]],
                        dtype=np.int,
                    )
                )
        care_homes_to_visit = np.array(care_homes_to_visit, dtype=int_vlen_type)
        if len(np.unique(list(chain(*households_to_visit)))) > 1:
            households_to_visit = np.array(
                households_to_visit, dtype=int_vlen_type
            )
            households_dset.create_dataset(
                "households_to_visit", data=households_to_visit,
            )
        if len(np.unique(list(chain(*care_homes_to_visit)))) > 1:
            care_homes_to_visit = np.array(
                care_homes_to_visit, dtype=int_vlen_type
            )
            households_dset.create_dataset(
                "care_homes_to_visit", data=care_homes_to_visit,
            )


def load_households_from_hdf5(
    file_path: str, chunk_size=50000, domain_super_areas=None
):
    """
    Loads households from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    logger.info("loading households...")
    households_list = []
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        households = f["households"]
        n_households = households.attrs["n_households"]
        n_chunks = int(np.ceil(n_households / chunk_size))
        for chunk in range(n_chunks):
            logger.info(f"Households chunk {chunk} of {n_chunks}")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            length = idx2 - idx1
            ids = np.empty(length, dtype=int)
            types = np.empty(length, dtype="S20")
            max_sizes = np.empty(length, dtype=float)
            households["id"].read_direct(ids, np.s_[idx1:idx2], np.s_[0:length])
            households["type"].read_direct(types, np.s_[idx1:idx2], np.s_[0:length])
            households["max_size"].read_direct(
                max_sizes, np.s_[idx1:idx2], np.s_[0:length]
            )
            super_areas = np.empty(length, dtype=int)
            households["super_area"].read_direct(
                super_areas, np.s_[idx1:idx2], np.s_[0:length]
            )
            for k in range(length):
                if domain_super_areas is not None:
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                household = Household(
                    area=None, type=types[k].decode(), max_size=max_sizes[k]
                )
                households_list.append(household)
                household.id = ids[k]
    return Households(households_list)

def restore_households_properties_from_hdf5(
    world: World, file_path: str, chunk_size=50000, domain_super_areas=None
):
    """
    Loads households from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    logger.info("restoring households...")
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        households = f["households"]
        if "households_to_visit" in households:
            has_household_visits = True
        else:
            has_household_visits = False
        if "care_homes_to_visit" in households:
            has_care_home_visits = True
        else:
            has_care_home_visits = False
        n_households = households.attrs["n_households"]
        n_chunks = int(np.ceil(n_households / chunk_size))
        for chunk in range(n_chunks):
            logger.info(f"Households chunk {chunk} of {n_chunks}")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            length = idx2 - idx1
            ids = read_dataset(households["id"], idx1, idx2)
            if has_household_visits:
                households_to_visit_list = read_dataset(households["households_to_visit"], idx1, idx2)
            if has_care_home_visits:
                care_homes_to_visit_list = read_dataset(households["care_homes_to_visit"], idx1, idx2)
            super_areas = read_dataset(households["super_area"], idx1, idx2)
            areas = read_dataset(households["area"], idx1, idx2)
            for k in range(length):
                if domain_super_areas is not None:
                    """
                    Note: if the relatives live outside the super area this will fail.
                    """
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                household = world.households.get_from_id(ids[k])
                area = world.areas.get_from_id(areas[k])
                household.area = area
                area.households.append(household)
                household.residents = tuple(household.people)
                # relatives
                if has_household_visits:
                    if households_to_visit_list[k][0] == nan_integer:
                        pass
                    else:
                        households_to_visit = []
                        for house_id in households_to_visit_list[k]:
                            households_to_visit.append(
                                world.households.get_from_id(house_id)
                            )
                        household.residences_to_visit["household"] = tuple(households_to_visit)
                if has_care_home_visits:
                    if care_homes_to_visit_list[k][0] == nan_integer:
                        pass
                    else:
                        care_homes_to_visit = []
                        for care_home_id in care_homes_to_visit_list[k]:
                            care_homes_to_visit.append(
                                world.care_homes.get_from_id(care_home_id)
                            )
                        household.residences_to_visit["care_home"] = tuple(care_homes_to_visit)
