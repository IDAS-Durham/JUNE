import h5py
import numpy as np
from june.groups import CareHome, CareHomes
from june.world import World

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
            n_residents = []
            n_workers = []
            contact_matrices_sizes = []
            contact_matrices_contacts = []
            contact_matrices_physical = []
            for carehome in care_homes[idx1:idx2]:
                ids.append(carehome.id)
                if carehome.area is None:
                    areas.append(nan_integer)
                else:
                    areas.append(carehome.area.id)
                n_residents.append(carehome.n_residents)
                n_workers.append(carehome.n_workers)

            ids = np.array(ids, dtype=np.int)
            areas = np.array(areas, dtype=np.int)
            n_residents = np.array(n_residents, dtype=np.float)
            n_workers = np.array(n_workers, dtype=np.float)
            if chunk == 0:
                care_homes_dset.attrs["n_care_homes"] = n_care_homes
                care_homes_dset.create_dataset("id", data=ids, maxshape=(None,))
                care_homes_dset.create_dataset("area", data=areas, maxshape=(None,))
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
                care_homes_dset["n_residents"].resize(newshape)
                care_homes_dset["n_residents"][idx1:idx2] = n_residents
                care_homes_dset["n_workers"].resize(newshape)
                care_homes_dset["n_workers"][idx1:idx2] = n_workers


def load_care_homes_from_hdf5(file_path: str, chunk_size=50000):
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
            ids = np.zeros(length, dtype=int)
            care_homes["id"].read_direct(ids, np.s_[idx1:idx2], np.s_[0:length])
            n_residents = np.empty(length, dtype=int)
            care_homes["n_residents"].read_direct(
                n_residents, np.s_[idx1:idx2], np.s_[0:length]
            )
            n_workers = np.empty(length, dtype=int)
            care_homes["n_workers"].read_direct(
                n_workers, np.s_[idx1:idx2], np.s_[0:length]
            )
            for k in range(idx2 - idx1):
                care_home = CareHome(
                    area=None, n_residents=n_residents[k], n_workers=n_workers[k]
                )
                care_home.id = ids[k]
                care_homes_list.append(care_home)
    return CareHomes(care_homes_list)


def restore_care_homes_properties_from_hdf5(
    world: World, file_path: str, chunk_size=50000
):
    """
    Loads carehomes from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    print("restoring care homes...")
    first_area_id = world.areas[0].id
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        first_care_home_id = world.care_homes[0].id
        carehomes = f["care_homes"]
        carehomes_list = []
        n_carehomes = carehomes.attrs["n_care_homes"]
        n_chunks = int(np.ceil(n_carehomes / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_carehomes)
            ids = carehomes["id"][idx1:idx2]
            areas = carehomes["area"][idx1:idx2]
            for k in range(idx2 - idx1):
                care_home = world.care_homes[ids[k] - first_care_home_id]
                if areas[k] == nan_integer:
                    area = None
                else:
                    area = world.areas[areas[k] - first_area_id]
                care_home.area = area
                area.care_home = care_home
