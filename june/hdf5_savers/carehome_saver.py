import h5py
import numpy as np

from june.groups import CareHome, CareHomes
from june.world import World
from .utils import read_dataset

nan_integer = -999


def save_care_homes_to_hdf5(
    care_homes: CareHomes, file_path: str, chunk_size: int = 50000
):
    """
    Saves the care_homes object to hdf5 format file ``file_path``. Currently for each person,
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
    n_care_homes = len(care_homes)
    n_chunks = int(np.ceil(n_care_homes / chunk_size))
    vlen_type = h5py.vlen_dtype(np.dtype("float64"))
    with h5py.File(file_path, "a") as f:
        care_homes_dset = f.create_group("care_homes")
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_care_homes)
            ids = []
            areas = []
            super_areas = []
            n_residents = []
            n_workers = []
            contact_matrices_sizes = []
            contact_matrices_contacts = []
            contact_matrices_physical = []
            for carehome in care_homes[idx1:idx2]:
                ids.append(carehome.id)
                if carehome.area is None:
                    areas.append(nan_integer)
                    super_areas.append(nan_integer)
                else:
                    areas.append(carehome.area.id)
                    super_areas.append(carehome.super_area.id)
                n_residents.append(carehome.n_residents)
                n_workers.append(carehome.n_workers)

            ids = np.array(ids, dtype=np.int64)
            areas = np.array(areas, dtype=np.int64)
            n_residents = np.array(n_residents, dtype=np.float64)
            n_workers = np.array(n_workers, dtype=np.float64)
            if chunk == 0:
                care_homes_dset.attrs["n_care_homes"] = n_care_homes
                care_homes_dset.create_dataset("id", data=ids, maxshape=(None,))
                care_homes_dset.create_dataset("area", data=areas, maxshape=(None,))
                care_homes_dset.create_dataset("super_area", data=super_areas, maxshape=(None,))
                care_homes_dset.create_dataset(
                    "n_residents", data=n_residents, maxshape=(None,)
                )
                care_homes_dset.create_dataset(
                    "n_workers", data=n_workers, maxshape=(None,)
                )
            else:
                newshape = (care_homes_dset["id"].shape[0] + ids.shape[0],)
                care_homes_dset["id"].resize(newshape)
                care_homes_dset["id"][idx1:idx2] = ids
                care_homes_dset["area"].resize(newshape)
                care_homes_dset["area"][idx1:idx2] = areas
                care_homes_dset["super_area"].resize(newshape)
                care_homes_dset["super_area"][idx1:idx2] = super_areas
                care_homes_dset["n_residents"].resize(newshape)
                care_homes_dset["n_residents"][idx1:idx2] = n_residents
                care_homes_dset["n_workers"].resize(newshape)
                care_homes_dset["n_workers"][idx1:idx2] = n_workers


def load_care_homes_from_hdf5(file_path: str, chunk_size=50000, domain_super_areas=None):
    """
    Loads carehomes from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        care_homes = f["care_homes"]
        care_homes_list = []
        n_carehomes = care_homes.attrs["n_care_homes"]
        n_chunks = int(np.ceil(n_carehomes / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_carehomes)
            length = idx2 - idx1
            ids = read_dataset(care_homes["id"], idx1, idx2)
            n_residents = read_dataset(care_homes["n_residents"], idx1, idx2)
            n_workers = read_dataset(care_homes["n_workers"], idx1, idx2)
            super_areas = read_dataset(care_homes["super_area"], idx1, idx2)
            for k in range(idx2 - idx1):
                if domain_super_areas is not None:
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                care_home = CareHome(
                    area=None, n_residents=n_residents[k], n_workers=n_workers[k]
                )
                care_home.id = ids[k]
                care_homes_list.append(care_home)
    return CareHomes(care_homes_list)


def restore_care_homes_properties_from_hdf5(
    world: World, file_path: str, chunk_size=50000, domain_super_areas = None 
):
    """
    Loads carehomes from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        carehomes = f["care_homes"]
        carehomes_list = []
        n_carehomes = carehomes.attrs["n_care_homes"]
        n_chunks = int(np.ceil(n_carehomes / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_carehomes)
            ids = carehomes["id"][idx1:idx2]
            areas = carehomes["area"][idx1:idx2]
            super_areas = carehomes["super_area"][idx1:idx2]
            for k in range(idx2 - idx1):
                if domain_super_areas is not None:
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                care_home = world.care_homes.get_from_id(ids[k])
                if areas[k] == nan_integer:
                    area = None
                else:
                    area = world.areas.get_from_id(areas[k])
                care_home.area = area
                area.care_home = care_home
