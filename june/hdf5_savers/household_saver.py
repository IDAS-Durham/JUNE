import h5py
import numpy as np
import logging
from collections import defaultdict, OrderedDict
from itertools import chain

from june.world import World
from june.groups import Household, Households, ExternalGroup
from june.mpi_setup import mpi_rank
from .utils import read_dataset

nan_integer = -999

int_vlen_type = h5py.vlen_dtype(np.dtype("int64"))
str_vlen_type = h5py.vlen_dtype(np.dtype("S20"))
logger = logging.getLogger("household_saver")
if mpi_rank > 0:
    logger.propagate = False


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

            ids = np.array(ids, dtype=np.int64)
            areas = np.array(areas, dtype=np.int64)
            super_areas = np.array(super_areas, dtype=np.int64)
            types = np.array(types, dtype="S20")
            max_sizes = np.array(max_sizes, dtype=np.float64)
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

        residences_to_visit_specs = []
        residences_to_visit_ids = []
        residences_to_visit_super_areas = []
        for household in households:
            if not household.residences_to_visit:
                residences_to_visit_specs.append(np.array(["none"], dtype="S20"))
                residences_to_visit_ids.append(np.array([nan_integer], dtype=np.int64))
                residences_to_visit_super_areas.append(
                    np.array([nan_integer], dtype=np.int64)
                )
            else:
                to_visit_ids = []
                to_visit_specs = []
                to_visit_super_areas = []
                for residence_type in household.residences_to_visit:
                    for residence_to_visit in household.residences_to_visit[
                        residence_type
                    ]:
                        to_visit_specs.append(residence_type)
                        to_visit_ids.append(residence_to_visit.id)
                        to_visit_super_areas.append(residence_to_visit.super_area.id)
                residences_to_visit_specs.append(np.array(to_visit_specs, dtype="S20"))
                residences_to_visit_ids.append(np.array(to_visit_ids, dtype=np.int64))
                residences_to_visit_super_areas.append(
                    np.array(to_visit_super_areas, dtype=np.int64)
                )

        if len(np.unique(list(chain(*residences_to_visit_ids)))) > 1:
            residences_to_visit_ids = np.array(
                residences_to_visit_ids, dtype=int_vlen_type
            )
            residences_to_visit_specs = np.array(
                residences_to_visit_specs, dtype=str_vlen_type
            )
            residences_to_visit_super_areas = np.array(
                residences_to_visit_super_areas, dtype=int_vlen_type
            )
        else:
            residences_to_visit_ids = np.array(residences_to_visit_ids, dtype=np.int64)
            residences_to_visit_specs = np.array(residences_to_visit_specs, dtype="S20")
            residences_to_visit_super_areas = np.array(
                residences_to_visit_super_areas, dtype=np.int64
            )
        households_dset.create_dataset(
            "residences_to_visit_ids",
            data=residences_to_visit_ids,
        )
        households_dset.create_dataset(
            "residences_to_visit_specs",
            data=residences_to_visit_specs,
        )
        households_dset.create_dataset(
            "residences_to_visit_super_areas",
            data=residences_to_visit_super_areas,
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
            logger.info(f"Loaded chunk {chunk} of {n_chunks}")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            length = idx2 - idx1
            ids = read_dataset(households["id"], idx1, idx2)
            types = read_dataset(households["type"], idx1, idx2)
            max_sizes = read_dataset(households["max_size"], idx1, idx2)
            super_areas = read_dataset(households["super_area"], idx1, idx2)
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
    world: World,
    file_path: str,
    chunk_size=50000,
    domain_super_areas=None,
    super_areas_to_domain_dict: dict = None,
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
        n_households = households.attrs["n_households"]
        n_chunks = int(np.ceil(n_households / chunk_size))
        for chunk in range(n_chunks):
            logger.info(f"Restored chunk {chunk} of {n_chunks}")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            length = idx2 - idx1
            ids = read_dataset(households["id"], idx1, idx2)
            super_areas = read_dataset(households["super_area"], idx1, idx2)
            areas = read_dataset(households["area"], idx1, idx2)
            residences_to_visit_ids = read_dataset(
                households["residences_to_visit_ids"], idx1, idx2
            )
            residences_to_visit_specs = read_dataset(
                households["residences_to_visit_specs"], idx1, idx2
            )
            residences_to_visit_super_areas = read_dataset(
                households["residences_to_visit_super_areas"], idx1, idx2
            )
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
                # visits
                visit_ids = residences_to_visit_ids[k]
                if visit_ids[0] == nan_integer:
                    continue
                visit_specs = residences_to_visit_specs[k]
                visit_super_areas = residences_to_visit_super_areas[k]
                for visit_id, visit_spec, visit_super_area in zip(
                    visit_ids, visit_specs, visit_super_areas
                ):
                    if (
                        domain_super_areas is not None
                        and visit_super_area not in domain_super_areas
                    ):
                        residence = ExternalGroup(
                            id=visit_id,
                            domain_id=super_areas_to_domain_dict[visit_super_area],
                            spec=visit_spec.decode(),
                        )
                    else:
                        visit_spec = visit_spec.decode()
                        if visit_spec == "household":
                            residence = world.households.get_from_id(visit_id)
                        elif visit_spec == "care_home":
                            residence = world.care_homes.get_from_id(visit_id)
                    household.residences_to_visit[visit_spec] = (
                        *household.residences_to_visit[visit_spec], residence
                    )
