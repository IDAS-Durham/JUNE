import h5py
import numpy as np
from june.groups import Schools, School

nan_integer = -999


def save_schools_to_hdf5(schools: Schools, file_path: str, chunk_size: int = 50000):
    """
    Saves the schools object to hdf5 format file ``file_path``. Currently for each person,
    the following values are stored:
    - id, n_pupils_max, n_teachers_max, n_teachers, age_min, age_max, sector, super_area, coordiantes

    Parameters
    ----------
    schools 
        population object
    file_path
        path of the saved hdf5 file
    chunk_size
        number of people to save at a time. Note that they have to be copied to be saved,
        so keep the number below 1e6.
    """
    n_schools = len(schools)
    n_chunks = int(np.ceil(n_schools / chunk_size))
    with h5py.File(file_path, "a", libver="latest") as f:
        schools_dset = f.create_group("schools")
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_schools)
            n_schools = len(schools)
            ids = []
            n_pupils_max = []
            n_teachers_max = []
            n_teachers = []
            age_min = []
            age_max = []
            sectors = []
            super_areas = []
            coordinates = []
            for school in schools:
                ids.append(school.id)
                if school.super_area is None:
                    super_areas.append(nan_integer)
                else:
                    super_areas.append(school.super_area.id)
                n_pupils_max.append(school.n_pupils_max)
                n_teachers_max.append(school.n_teachers_max)
                n_teachers.append(school.n_teachers)
                age_min.append(school.age_min)
                age_max.append(school.age_max)
                sectors.append(school.sector.encode("ascii", "ignore"))
                coordinates.append(np.array(school.coordinates))

            ids = np.array(ids, dtype=np.int)
            super_areas = np.array(super_areas, dtype=np.int)
            n_pupils_max = np.array(n_pupils_max, dtype=np.int)
            n_teachers_max = np.array(n_teachers_max, dtype=np.int)
            n_teachers = np.array(n_teachers, dtype=np.int)
            age_min = np.array(age_min, dtype=np.int)
            age_max = np.array(age_max, dtype=np.int)
            sectors = np.array(sectors, dtype="S20")
            coordinates = np.array(coordinates, dtype=np.float)
            if chunk == 0:
                schools_dset.attrs["n_schools"] = n_schools
                schools_dset.create_dataset("id", data=ids)
                schools_dset.create_dataset("super_area", data=super_areas)
                schools_dset.create_dataset("n_teachers_max", data=n_teachers_max)
                schools_dset.create_dataset("n_pupils_max", data=n_pupils_max)
                schools_dset.create_dataset("n_teachers", data=n_teachers)
                schools_dset.create_dataset("age_min", data=age_min)
                schools_dset.create_dataset("age_max", data=age_max)
                schools_dset.create_dataset("sector", data=sectors)
                schools_dset.create_dataset("coordinates", data=coordinates)
            else:
                schools_dset["id"][idx1:idx2] = ids
                schools_dset["super_area"][idx1:idx2] = super_areas
                schools_dset["n_teachers_max"][idx1:idx2] = n_teachers_max
                schools_dset["n_pupils_max"][idx1:idx2] = n_pupils_max
                schools_dset["n_teachers"][idx1:idx2] = n_teachers
                schools_dset["age_min"][idx1:idx2] = age_min
                schools_dset["age_max"][idx1:idx2] = age_max
                schools_dset["sector"][idx1:idx2] = sectors
                schools_dset["coordinates"][idx1:idx2] = coordinates

def load_schools_from_hdf5(file_path: str, chunk_size: int = 50000):
    """
    Loads schools from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r") as f:
        schools = f["schools"]
        schools_list = list()
        n_schools = schools.attrs["n_schools"]
        n_chunks = int(np.ceil(n_schools / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_schools)
            ids = schools["id"]
            super_areas = schools["super_area"][idx1:idx2]
            n_teachers_max = schools["n_teachers_max"][idx1:idx2]
            n_teachers = schools["n_teachers"][idx1:idx2]
            n_pupils_max = schools["n_pupils_max"][idx1:idx2]
            age_min = schools["age_min"][idx1:idx2]
            age_max = schools["age_max"][idx1:idx2]
            coordinates = schools["coordinates"][idx1:idx2]
            sectors = schools["sector"]
            for k in range(idx2 - idx1):
                super_area = super_areas[k]
                if super_area == nan_integer:
                    super_area = None
                school = School(
                    coordinates[k],
                    n_pupils_max[k],
                    n_teachers_max[k],
                    age_min[k],
                    age_max[k],
                    sectors[k].decode(),
                )
                school.id = ids[k]
                school.n_teachers = n_teachers[k]
                schools_list.append(school)
    return Schools(schools_list)
