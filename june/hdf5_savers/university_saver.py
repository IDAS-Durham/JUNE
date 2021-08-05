import h5py
import numpy as np

from june.groups import University, Universities
from .utils import read_dataset

nan_integer = -999


def save_universities_to_hdf5(universities: Universities, file_path: str):
    """
    Saves the universities object to hdf5 format file ``file_path``. Currently for each person,
    the following values are stored:
    - id, n_pupils_max,  age_min, age_max, sector 

    Parameters
    ----------
    universities 
        population object
    file_path
        path of the saved hdf5 file
    chunk_size
        number of people to save at a time. Note that they have to be copied to be saved,
        so keep the number below 1e6.
    """
    n_universities = len(universities)
    with h5py.File(file_path, "a") as f:
        universities_dset = f.create_group("universities")
        ids = []
        n_students_max = []
        n_years = []
        ukprns = []
        areas = []
        coordinates = []
        for university in universities:
            ids.append(university.id)
            n_students_max.append(university.n_students_max)
            n_years.append(university.n_years)
            coordinates.append(np.array(university.coordinates, dtype=np.float64))
            ukprns.append(university.ukprn)
            if university.area is None:
                areas.append(nan_integer)
            else:
                areas.append(university.area.id)

        ids = np.array(ids, dtype=np.int64)
        n_students_max = np.array(n_students_max, dtype=np.int64)
        n_years = np.array(n_years, dtype=np.int64)
        ukprns = np.array(ukprns, dtype=np.int64)
        areas = np.array(areas, dtype=np.int64)
        coordinates = np.array(coordinates, dtype=np.float64)
        universities_dset.attrs["n_universities"] = n_universities
        universities_dset.create_dataset("id", data=ids)
        universities_dset.create_dataset("n_students_max", data=n_students_max)
        universities_dset.create_dataset("n_years", data=n_years)
        universities_dset.create_dataset("area", data=areas)
        universities_dset.create_dataset("coordinates", data=coordinates)
        universities_dset.create_dataset("ukprns", data=ukprns)


def load_universities_from_hdf5(
    file_path: str, chunk_size: int = 50000, domain_areas=None
):
    """
    Loads universities from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        universities = f["universities"]
        universities_list = []
        n_universities = universities.attrs["n_universities"]
        ids = read_dataset(universities["id"])
        n_students_max = read_dataset(universities["n_students_max"])
        n_years = read_dataset(universities["n_years"])
        ukprns = read_dataset(universities["ukprns"])
        areas = read_dataset(universities["area"])
        coordinates = read_dataset(universities["coordinates"])
        for k in range(n_universities):
            if domain_areas is not None:
                area = areas[k]
                if area == nan_integer:
                    raise ValueError(
                        "if ``domain_areas`` is True, I expect not Nones areas."
                    )
                if area not in domain_areas:
                    continue
            university = University(
                n_students_max=n_students_max[k],
                n_years=n_years[k],
                ukprn=ukprns[k],
                coordinates=coordinates[k]
            )
            university.id = ids[k]
            universities_list.append(university)
    return Universities(universities_list)


def restore_universities_properties_from_hdf5(
    world, file_path: str, chunk_size: int = 50000, domain_areas=None
):
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        universities = f["universities"]
        universities_list = []
        n_universities = universities.attrs["n_universities"]
        ids = np.empty(n_universities, dtype=int)
        universities["id"].read_direct(
            ids, np.s_[0:n_universities], np.s_[0:n_universities]
        )
        areas = np.empty(n_universities, dtype=int)
        universities["area"].read_direct(
            areas, np.s_[0:n_universities], np.s_[0:n_universities]
        )
        for k in range(n_universities):
            if domain_areas is not None:
                area = areas[k]
                if area == nan_integer:
                    raise ValueError(
                        "if ``domain_areas`` is True, I expect not Nones super areas."
                    )
                if area not in domain_areas:
                    continue
            university = world.universities.get_from_id(ids[k])
            area = areas[k]
            if area == nan_integer:
                area = None
            else:
                area = world.areas.get_from_id(area)
            university.area = area
