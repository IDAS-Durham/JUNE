import numpy as np
import h5py
from typing import List
from itertools import chain

from june.hdf5_savers.utils import read_dataset, write_dataset
from june.epidemiology.infection import Immunity

int_vlen_type = h5py.vlen_dtype(np.dtype("int64"))
float_vlen_type = h5py.vlen_dtype(np.dtype("float64"))

nan_integer = -999
nan_float = -999.0


def save_immunities_to_hdf5(hdf5_file_path: str, immunities: List[Immunity]):
    """
    Saves infections data to hdf5.

    Parameters
    ----------
    hdf5_file_path
        hdf5 path to save symptoms
    immunities
        list of Immunity objects
    chunk_size
        number of hdf5 chunks to use while saving
    """
    with h5py.File(hdf5_file_path, "a") as f:
        g = f.create_group("immunities")
        n_immunities = len(immunities)
        g.attrs["n_immunities"] = n_immunities
        if n_immunities == 0:
            return
        susc_infection_ids = []
        susc_susceptibilities = []
        lengths = []
        for imm in immunities:
            inf_ids = []
            suscs = []
            for key, value in imm.susceptibility_dict.items():
                inf_ids.append(key)
                suscs.append(value)
            if len(inf_ids) == 0:
                inf_ids = [nan_integer]
                suscs = [nan_float]
            susc_infection_ids.append(np.array(inf_ids, dtype=np.int64))
            susc_susceptibilities.append(np.array(suscs, dtype=np.float64))
            lengths.append(len(suscs))
        if len(np.unique(lengths)) > 1:
            susc_infection_ids = np.array(susc_infection_ids, dtype=int_vlen_type)
            susc_susceptibilities = np.array(
                susc_susceptibilities, dtype=float_vlen_type
            )
        else:
            susc_infection_ids = np.array(susc_infection_ids, dtype=np.int64)
            susc_susceptibilities = np.array(susc_susceptibilities, dtype=np.float64)
        g.create_dataset(
            "susc_infection_ids",
            data=susc_infection_ids,
        )
        g.create_dataset(
            "susc_susceptibilities",
            data=susc_susceptibilities,
        )


def load_immunities_from_hdf5(hdf5_file_path: str, chunk_size=50000):
    """
    Loads immunities data from hdf5.

    Parameters
    ----------
    hdf5_file_path
        hdf5 path to load from
    chunk_size
        number of hdf5 chunks to use while loading
    """
    immunities = []
    with h5py.File(hdf5_file_path, "r") as f:
        g = f["immunities"]
        n_immunities = g.attrs["n_immunities"]
        if n_immunities == 0:
            return []
        n_chunks = int(np.ceil(n_immunities / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_immunities)
            susc_infection_ids = read_dataset(g["susc_infection_ids"], idx1, idx2)
            susc_susceptibilities = read_dataset(g["susc_susceptibilities"], idx1, idx2)
            length = idx2 - idx1
            for k in range(length):
                if susc_infection_ids[k][0] == nan_integer:
                    immunity = Immunity()
                else:
                    susceptibilities_dict = {
                        key: value
                        for key, value in zip(
                            susc_infection_ids[k], susc_susceptibilities[k]
                        )
                    }
                    immunity = Immunity(susceptibilities_dict)
                immunities.append(immunity)
    return immunities
