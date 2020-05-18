import h5py
import numpy as np
from june.groups import Household, Households

nan_integer = -999


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
    with h5py.File(file_path, "a", libver="latest") as f:
        households_dset = f.create_group("households")
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            ids = []
            areas = []
            communals = []
            max_sizes = []
            for household in households:
                ids.append(household.id)
                if household.area is None:
                    areas.append(nan_integer)
                else:
                    areas.append(household.area.id)
                communals.append(household.communal)
                max_sizes.append(household.max_size)
            ids = np.array(ids, dtype=np.int)
            areas = np.array(areas, dtype=np.int)
            communals = np.array(communals, dtype=np.bool)
            max_sizes = np.array(max_sizes, dtype=np.float)
            if chunk == 0:
                households_dset.attrs["n_households"] = n_households
                households_dset.create_dataset("id", data=ids)
                households_dset.create_dataset("area", data=areas)
                households_dset.create_dataset("communal", data=communals)
                households_dset.create_dataset("max_size", data=max_sizes)
            else:
                households_dset["id"][idx1:idx2] = ids
                households_dset["area"][idx1:idx2] = areas 
                households_dset["communal"][idx1:idx2] = communals
                households_dset["max_size"][idx1:idx2] = max_sizes

def load_households_from_hdf5(file_path: str, chunk_size=50000):
    """
    Loads households from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r") as f:
        households = f["households"]
        households_list = list()
        chunk_size = 50000
        n_households = households.attrs["n_households"]
        n_chunks = int(np.ceil(n_households / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            ids = households["id"][idx1:idx2]
            communals = households["communal"][idx1:idx2]
            areas = households["area"][idx1:idx2]
            max_sizes = households["max_size"][idx1:idx2]
            for k in range(idx2 - idx1):
                area = areas[k]
                if area == nan_integer:
                    area = None
                household = Household(
                    communal=communals[k], area=area, max_size=max_sizes[k]
                )
                household.id = ids[k]
                households_list.append(household)
    return Households(households_list)
