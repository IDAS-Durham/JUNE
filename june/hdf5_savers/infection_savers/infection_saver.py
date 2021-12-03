import numpy as np
import h5py
from collections import defaultdict
from typing import List

from june.hdf5_savers.utils import read_dataset, write_dataset
from june.epidemiology.infection import infection as infection_module
from june.epidemiology.infection import Infection
from .symptoms_saver import save_symptoms_to_hdf5, load_symptoms_from_hdf5
from .transmission_saver import save_transmissions_to_hdf5, load_transmissions_from_hdf5

int_vlen_type = h5py.vlen_dtype(np.dtype("int64"))
float_vlen_type = h5py.vlen_dtype(np.dtype("float64"))

def save_infection_classes_to_hdf5(
    hdf5_file_path: str,
    infections: List[Infection],
    chunk_size: int = 50000,
):
    n_infections = len(infections)
    n_chunks = int(np.ceil(n_infections / chunk_size))
    with h5py.File(hdf5_file_path, "a") as f:
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_infections)
            tosave = []
            for index in range(idx1, idx2):
                infection = infections[index]
                tosave.append(infection.__class__.__name__.encode("ascii", "ignore"))
            data = np.array(tosave, dtype="S20")
            write_dataset(
                group=f["infections"],
                dataset_name="infection_class",
                data=data,
                index1=idx1,
                index2=idx2,
            )


def save_infections_to_hdf5(
    hdf5_file_path: str,
    infections: List[Infection],
    chunk_size: int = 50000,
):
    """
    Saves infections data to hdf5.

    Parameters
    ----------
    attributes_to_save
        attributes to save from each symptom
    hdf5_file_path
        hdf5 path to save symptoms
    symptoms
        list of symptom objects
    chunk_size
        number of hdf5 chunks to use while saving
    """
    with h5py.File(hdf5_file_path, "a") as f:
        f.create_group("infections")
        n_infections = len(infections)
        f["infections"].attrs["n_infections"] = n_infections
        if n_infections == 0:
            return
        symptoms_list = [infection.symptoms for infection in infections]
        transmission_list = [infection.transmission for infection in infections]
        save_symptoms_to_hdf5(
            symptoms_list=symptoms_list,
            hdf5_file_path=hdf5_file_path,
            chunk_size=chunk_size,
        )
        save_transmissions_to_hdf5(
            transmissions=transmission_list,
            hdf5_file_path=hdf5_file_path,
            chunk_size=chunk_size,
        )
        attributes_to_save = ["start_time"]
        n_chunks = int(np.ceil(n_infections / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_infections)
            attribute_dict = defaultdict(list)
            for index in range(idx1, idx2):
                infection = infections[index]
                for attribute_name in attributes_to_save:
                    attribute = getattr(infection, attribute_name)
                    if attribute is None:
                        attribute_dict[attribute_name].append(np.nan)
                    else:
                        attribute_dict[attribute_name].append(attribute)
            for attribute_name in attributes_to_save:
                data = np.array(attribute_dict[attribute_name], dtype=np.float64)
                write_dataset(
                    group=f["infections"],
                    dataset_name=attribute_name,
                    data=data,
                    index1=idx1,
                    index2=idx2,
                )
    save_infection_classes_to_hdf5(hdf5_file_path = hdf5_file_path, infections=infections, chunk_size=chunk_size)

def load_infections_from_hdf5(hdf5_file_path: str, chunk_size=50000):
    """
    Loads infections data from hdf5.

    Parameters
    ----------
    hdf5_file_path
        hdf5 path to load from
    chunk_size
        number of hdf5 chunks to use while loading
    """
    infections = []
    with h5py.File(hdf5_file_path, "r") as f:
        infections_group = f["infections"]
        n_infections = infections_group.attrs["n_infections"]
        if n_infections == 0:
            return []
        symptoms_list = load_symptoms_from_hdf5(
            hdf5_file_path=hdf5_file_path, chunk_size=chunk_size
        )
        transmissions = load_transmissions_from_hdf5(
            hdf5_file_path=hdf5_file_path, chunk_size=chunk_size
        )
        trans_symp_index = 0
        n_infections = infections_group.attrs["n_infections"]
        n_chunks = int(np.ceil(n_infections / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_infections)
            attribute_dict = {}
            for attribute_name in infections_group.keys():
                if attribute_name in ["symptoms", "transmissions", "infection_class"]:
                    continue
                attribute_dict[attribute_name] = read_dataset(
                    infections_group[attribute_name], idx1, idx2
                )
            for index in range(idx2 - idx1):
                infection_class_str = infections_group["infection_class"][trans_symp_index].decode()
                infection_class = getattr(infection_module, infection_class_str)
                infection = infection_class(
                    transmission=transmissions[trans_symp_index],
                    symptoms=symptoms_list[trans_symp_index],
                )
                trans_symp_index += 1
                for attribute_name in attribute_dict:
                    attribute_value = attribute_dict[attribute_name][index]
                    if attribute_value == np.nan:
                        attribute_value = None
                    setattr(infection, attribute_name, attribute_value)
                infections.append(infection)
    return infections
