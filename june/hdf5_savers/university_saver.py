import h5py
import numpy as np
from june.groups import University, Universities

nan_integer = -999


def save_universities_to_hdf5(universities: Universities, file_path: str):
    """
    Saves the universities object to hdf5 format file ``file_path``. Currently for each person,
    the following values are stored:
    - id, n_pupils_max,  age_min, age_max, sector, coordiantes

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
        coordinates = []
        ukprns = []
        super_areas = []
        for university in universities:
            ids.append(university.id)
            n_students_max.append(university.n_students_max)
            coordinates.append(np.array(university.coordinates))
            n_years.append(university.n_years)
            ukprns.append(university.ukprn)
            if university.super_area is None:
                super_areas.append(nan_integer)
            else:
                super_areas.append(university.super_area.id)

        ids = np.array(ids, dtype=np.int)
        n_students_max = np.array(n_students_max, dtype=np.int)
        coordinates = np.array(coordinates, dtype=np.float)
        n_years = np.array(n_years, dtype=np.int)
        ukprns = np.array(ukprns, dtype=np.int)
        super_areas = np.array(super_areas, dtype=np.int)
        universities_dset.attrs["n_universities"] = n_universities
        universities_dset.create_dataset("id", data=ids)
        universities_dset.create_dataset("n_students_max", data=n_students_max)
        universities_dset.create_dataset("n_years", data=n_years)
        universities_dset.create_dataset("super_area", data=super_areas)
        universities_dset.create_dataset("ukprns", data=ukprns)
        universities_dset.create_dataset(
            "coordinates", data=coordinates,
        )


def load_universities_from_hdf5(file_path: str, chunk_size: int = 50000):
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
        ids = np.empty(n_universities, dtype=int)
        universities["id"].read_direct(
            ids, np.s_[0:n_universities], np.s_[0:n_universities]
        )
        n_students_max = np.empty(n_universities, dtype=int)
        universities["n_students_max"].read_direct(
            n_students_max, np.s_[0:n_universities], np.s_[0:n_universities]
        )
        n_years = np.empty(n_universities, dtype=int)
        universities["n_years"].read_direct(
            n_years, np.s_[0:n_universities], np.s_[0:n_universities]
        )
        coordinates = np.empty((n_universities, 2), dtype=float)
        universities["coordinates"].read_direct(
            coordinates, np.s_[0:n_universities], np.s_[0:n_universities]
        )
        ukprns = np.empty(n_universities, dtype=int)
        universities["ukprns"].read_direct(
            ukprns, np.s_[0:n_universities], np.s_[0:n_universities]
        )
        for k in range(n_universities):
            university = University(
                coordinates=coordinates[k],
                n_students_max=n_students_max[k],
                n_years=n_years[k],
                ukprn=ukprns[k],
            )
            university.id = ids[k]
            universities_list.append(university)
    return Universities(universities_list)

def restore_universities_properties_from_hdf5(world, file_path: str, chunk_size: int = 50000):
    first_uni_id = world.universities[0].id
    first_super_area_id = world.super_areas[0].id
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        universities = f["universities"]
        universities_list = []
        n_universities = universities.attrs["n_universities"]
        ids = np.empty(n_universities, dtype=int)
        universities["id"].read_direct(
            ids, np.s_[0:n_universities], np.s_[0:n_universities]
        )
        super_areas = np.empty(n_universities, dtype=int)
        universities["super_area"].read_direct(
            super_areas, np.s_[0:n_universities], np.s_[0:n_universities]
        )
        for k in range(n_universities):
            university = world.universities[ids[k] - first_uni_id]
            super_area = super_areas[k]
            if super_area == nan_integer:
                super_area = None
            else:
                super_area = world.super_areas[super_area - first_uni_id]
            university.super_area = super_area
