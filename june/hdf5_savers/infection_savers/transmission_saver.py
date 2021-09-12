import numpy as np
import h5py
from collections import defaultdict
from typing import List

from june import paths
from june.epidemiology.infection import (
    TransmissionGamma,
    Transmission,
    TransmissionConstant,
    TransmissionXNExp,
)
from june.hdf5_savers.utils import read_dataset, write_dataset

str_to_class = {
    "TransmissionXNExp": TransmissionXNExp,
    "TransmissionGamma": TransmissionGamma,
    "TransmissionConstant": TransmissionConstant,
}
attributes_to_save_dict = {
    "TransmissionXNExp": ["time_first_infectious", "norm_time", "n", "norm", "alpha"],
    "TransmissionGamma": ["shape", "shift", "scale", "norm"],
    "TransmissionConstant": ["probability"],
}


def save_transmissions_to_hdf5(
    hdf5_file_path: str,
    transmissions: List[Transmission],
    chunk_size: int = 50000,
):
    """
    Saves transmissions data to hdf5. The transmission type is inferred from the first
    element of the list.

    Parameters
    ----------
    attributes_to_save
        attributes to save from each transmission
    hdf5_file_path
        hdf5 path to save transmissions
    transmissions
        list of transmission objects
    chunk_size
        number of hdf5 chunks to use while saving
    """
    with h5py.File(hdf5_file_path, "a") as f:
        if "infections" not in f:
            f.create_group("infections")
        f["infections"].create_group("transmissions")
        transmissions_group = f["infections"]["transmissions"]
        n_transsmissions = len(transmissions)
        transmissions_group.attrs["n_transsmissions"] = n_transsmissions
        transmission_type = transmissions[0].__class__.__name__
        transmissions_group.attrs["transmission_type"] = transmission_type
        n_chunks = int(np.ceil(n_transsmissions / chunk_size))
        attributes_to_save = attributes_to_save_dict[transmission_type]
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_transsmissions)
            attribute_dict = defaultdict(list)
            for index in range(idx1, idx2):
                transmission = transmissions[index]
                for attribute_name in attributes_to_save:
                    attribute = getattr(transmission, attribute_name)
                    if attribute is None:
                        attribute_dict[attribute_name].append(np.nan)
                    else:
                        attribute_dict[attribute_name].append(attribute)
            for attribute_name in attributes_to_save:
                attribute_dict[attribute_name] = np.array(
                    attribute_dict[attribute_name], dtype=np.float64
                )
            for attribute_name in attributes_to_save:
                write_dataset(
                    group=transmissions_group,
                    dataset_name=attribute_name,
                    data=attribute_dict[attribute_name],
                    index1=idx1,
                    index2=idx2,
                )


def load_transmissions_from_hdf5(hdf5_file_path: str, chunk_size=50000):
    """
    Loads transmissions data from hdf5.

    Parameters
    ----------
    hdf5_file_path
        hdf5 path to load from
    chunk_size
        number of hdf5 chunks to use while loading
    """
    transmissions = []
    with h5py.File(hdf5_file_path, "r") as f:
        transmissions_group = f["infections"]["transmissions"]
        n_transsmissions = transmissions_group.attrs["n_transsmissions"]
        transmission_type = transmissions_group.attrs["transmission_type"]
        transmission_class = str_to_class[transmission_type]
        n_chunks = int(np.ceil(n_transsmissions / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_transsmissions)
            attribute_dict = {}
            for attribute_name in transmissions_group.keys():
                attribute_dict[attribute_name] = read_dataset(
                    transmissions_group[attribute_name], idx1, idx2
                )
            for index in range(idx2 - idx1):
                transmission = transmission_class()
                for attribute_name in attribute_dict:
                    attribute_value = attribute_dict[attribute_name][index]
                    if attribute_value == np.nan:
                        attribute_value = None
                    setattr(transmission, attribute_name, attribute_value)
                transmissions.append(transmission)
    return transmissions
