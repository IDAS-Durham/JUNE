import numpy as np
import h5py
from collections import defaultdict
from typing import List

from june.hdf5_savers.utils import read_dataset, write_dataset
from june.epidemiology.infection import Symptoms, SymptomTag

int_vlen_type = h5py.vlen_dtype(np.dtype("int64"))
float_vlen_type = h5py.vlen_dtype(np.dtype("float64"))


def save_symptoms_to_hdf5(
    hdf5_file_path: str,
    symptoms_list: List[Symptoms],
    chunk_size: int = 50000,
):
    """
    Saves symptoms data to hdf5.

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
        if "infections" not in f:
            f.create_group("infections")
        f["infections"].create_group("symptoms")
        symptoms_group = f["infections"]["symptoms"]
        n_symptoms = len(symptoms_list)
        symptoms_group.attrs["n_symptoms"] = n_symptoms
        n_chunks = int(np.ceil(n_symptoms / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_symptoms)
            attribute_dict = {}
            max_tag_list = []
            tag_list = []
            max_severity_list = []
            stage_list = []
            time_of_symptoms_onset_list = []
            for index in range(idx1, idx2):
                symptoms = symptoms_list[index]
                max_tag_list.append(symptoms.max_tag.value)
                tag_list.append(symptoms.tag.value)
                max_severity_list.append(symptoms.max_severity)
                stage_list.append(symptoms.stage)
                time_of_symptoms_onset_list.append(symptoms.time_of_symptoms_onset)
            attribute_dict["max_tag"] = np.array(max_tag_list, dtype=np.int64)
            attribute_dict["tag"] = np.array(tag_list, dtype=np.int64)
            attribute_dict["max_severity"] = np.array(max_severity_list, dtype=np.float64)
            attribute_dict["stage"] = np.array(stage_list, dtype=np.int64)
            attribute_dict["time_of_symptoms_onset"] = np.array(
                time_of_symptoms_onset_list, dtype=np.float64
            )
            for attribute_name, attribute_value in attribute_dict.items():
                write_dataset(
                    group=symptoms_group,
                    dataset_name=attribute_name,
                    data=attribute_value,
                    index1=idx1,
                    index2=idx2,
                )
        trajectory_times_list = []
        trajectory_symptom_list = []
        trajectory_lengths = []
        for symptoms in symptoms_list:
            times = []
            symps = []
            for time, symp in symptoms.trajectory:
                times.append(time)
                symps.append(symp.value)
            trajectory_times_list.append(np.array(times, dtype=np.float64))
            trajectory_symptom_list.append(np.array(symps, dtype=np.int64))
            trajectory_lengths.append(len(times))
        if len(np.unique(trajectory_lengths)) == 1:
            write_dataset(
                group=symptoms_group,
                dataset_name="trajectory_times",
                data=np.array(trajectory_times_list, dtype=float),
            )
            write_dataset(
                group=symptoms_group,
                dataset_name="trajectory_symptoms",
                data=np.array(trajectory_symptom_list, dtype=int),
            )
        else:
            write_dataset(
                group=symptoms_group,
                dataset_name="trajectory_times",
                data=np.array(trajectory_times_list, dtype=float_vlen_type),
            )
            write_dataset(
                group=symptoms_group,
                dataset_name="trajectory_symptoms",
                data=np.array(trajectory_symptom_list, dtype=int_vlen_type),
            )


def load_symptoms_from_hdf5(hdf5_file_path: str, chunk_size=50000):
    """
    Loads symptoms data from hdf5.

    Parameters
    ----------
    hdf5_file_path
        hdf5 path to load from
    chunk_size
        number of hdf5 chunks to use while loading
    """
    symptoms = []
    with h5py.File(hdf5_file_path, "r") as f:
        symptoms_group = f["infections"]["symptoms"]
        n_symptoms = symptoms_group.attrs["n_symptoms"]
        n_chunks = int(np.ceil(n_symptoms / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_symptoms)
            max_tag_list = read_dataset(symptoms_group["max_tag"], idx1, idx2)
            tag_list = read_dataset(symptoms_group["tag"], idx1, idx2)
            max_severity_list = read_dataset(symptoms_group["max_severity"], idx1, idx2)
            stage_list = read_dataset(symptoms_group["stage"], idx1, idx2)
            time_of_symptoms_onset_list = read_dataset(
                symptoms_group["time_of_symptoms_onset"], idx1, idx2
            )
            trajectory_times_list = read_dataset(
                symptoms_group["trajectory_times"], idx1, idx2
            )
            trajectory_symptom_list = read_dataset(
                symptoms_group["trajectory_symptoms"], idx1, idx2
            )
            for index in range(idx2 - idx1):
                symptom = Symptoms()
                symptom.tag = SymptomTag(tag_list[index])
                symptom.max_tag = SymptomTag(max_tag_list[index])
                symptom.stage = stage_list[index]
                symptom.max_severity = max_severity_list[index]
                symptom.time_of_symptoms_onset = time_of_symptoms_onset_list[index]
                symptom.trajectory = tuple(
                    [
                        (time, SymptomTag(symp))
                        for time, symp in zip(
                            trajectory_times_list[index], trajectory_symptom_list[index]
                        )
                    ]
                )
                symptoms.append(symptom)
    return symptoms
