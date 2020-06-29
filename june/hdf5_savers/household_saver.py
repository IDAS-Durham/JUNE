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
    vlen_type = h5py.vlen_dtype(np.dtype("float64"))
    with h5py.File(file_path, "a") as f:
        households_dset = f.create_group("households")
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            ids = []
            areas = []
            types = []
            max_sizes = []
            for household in households[idx1:idx2]:
                ids.append(household.id)
                if household.area is None:
                    areas.append(nan_integer)
                else:
                    areas.append(household.area.id)
                if household.type is None:
                    types.append(" ".encode("ascii", "ignore"))
                else:
                    types.append(household.type.encode("ascii", "ignore"))
                max_sizes.append(household.max_size)

            ids = np.array(ids, dtype=np.int)
            areas = np.array(areas, dtype=np.int)
            types = np.array(types, dtype="S15")
            max_sizes = np.array(max_sizes, dtype=np.float)
            if chunk == 0:
                households_dset.attrs["n_households"] = n_households
                households_dset.create_dataset("id", data=ids, maxshape=(None,))
                households_dset.create_dataset("area", data=areas, maxshape=(None,))
                households_dset.create_dataset("type", data=types, maxshape=(None,))
                households_dset.create_dataset("max_size", data=max_sizes, maxshape=(None,))
            else:
                newshape = (households_dset["id"].shape[0] + ids.shape[0],)
                households_dset["id"].resize(newshape)
                households_dset["id"][idx1:idx2] = ids
                households_dset["area"].resize(newshape)
                households_dset["area"][idx1:idx2] = areas 
                households_dset["type"].resize(newshape)
                households_dset["type"][idx1:idx2] = types
                households_dset["max_size"].resize(newshape)
                households_dset["max_size"][idx1:idx2] = max_sizes

def load_households_from_hdf5(file_path: str, chunk_size=50000):
    """
    Loads households from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    print("loading households from hdf5 ", end="")
    with h5py.File(file_path, "r") as f:
        households = f["households"]
        households_list = list()
        n_households = households.attrs["n_households"]
        n_chunks = int(np.ceil(n_households / chunk_size))
        for chunk in range(n_chunks):
            print(".", end="")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            ids = households["id"][idx1:idx2]
            types = households["type"][idx1:idx2]
            areas = households["area"][idx1:idx2]
            max_sizes = households["max_size"][idx1:idx2]
            for k in range(idx2 - idx1):
                area = areas[k]
                if area == nan_integer:
                    area = None
                type = types[k]
                if type.decode() == " ":
                    type = None
                else:
                    type = type.decode()
                household = Household(
                    type=type, area=area, max_size=max_sizes[k]
                )
                household.id = ids[k]
                households_list.append(household)
    print("\n", end="")
    return Households(households_list)
