import h5py
import numpy as np

from june.groups import Schools, School
from june.world import World

nan_integer = -999

int_vlen_type = h5py.vlen_dtype(np.dtype("int64"))

def save_schools_to_hdf5(schools: Schools, file_path: str, chunk_size: int = 50000):
    """
    Saves the schools object to hdf5 format file ``file_path``. Currently for each person,
    the following values are stored:
    - id, n_pupils_max,  age_min, age_max, sector, coordiantes

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
    with h5py.File(file_path, "a") as f:
        schools_dset = f.create_group("schools")
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_schools)
            ids = []
            n_pupils_max = []
            age_min = []
            age_max = []
            sectors = []
            coordinates = []
            areas = []
            n_classrooms = []
            years = []
            for school in schools[idx1:idx2]:
                ids.append(school.id)
                n_pupils_max.append(school.n_pupils_max)
                age_min.append(school.age_min)
                age_max.append(school.age_max)
                if type(school.sector) is float:
                    sectors.append(" ".encode("ascii", "ignore"))
                else:
                    sectors.append(school.sector.encode("ascii", "ignore"))
                if school.area is None:
                    areas.append(nan_integer)
                else:
                    areas.append(school.area.id)
                coordinates.append(np.array(school.coordinates))
                n_classrooms.append(school.n_classrooms)
                years.append(np.array(school.years))

            ids = np.array(ids, dtype=np.int)
            n_pupils_max = np.array(n_pupils_max, dtype=np.int)
            age_min = np.array(age_min, dtype=np.int)
            age_max = np.array(age_max, dtype=np.int)
            sectors = np.array(sectors, dtype="S20")
            areas = np.array(areas, dtype=np.int)
            coordinates = np.array(coordinates, dtype=np.float)
            n_classrooms = np.array(n_classrooms, dtype=np.int)
            years = np.array(years, dtype=int_vlen_type)
            if chunk == 0:
                schools_dset.attrs["n_schools"] = n_schools
                schools_dset.create_dataset("id", data=ids, maxshape=(None,))
                schools_dset.create_dataset(
                    "n_pupils_max", data=n_pupils_max, maxshape=(None,)
                )
                schools_dset.create_dataset("age_min", data=age_min, maxshape=(None,))
                schools_dset.create_dataset("age_max", data=age_max, maxshape=(None,))
                schools_dset.create_dataset("sector", data=sectors, maxshape=(None,))
                schools_dset.create_dataset(
                    "coordinates",
                    data=coordinates,
                    maxshape=(None, coordinates.shape[1]),
                )
                schools_dset.create_dataset("area", data=areas, maxshape=(None,))
                schools_dset.create_dataset("n_classrooms", data=n_classrooms, maxshape=(None,))
                schools_dset.create_dataset("years", data=years) 
            else:
                newshape = (schools_dset["id"].shape[0] + ids.shape[0],)
                schools_dset["id"].resize(newshape)
                schools_dset["id"][idx1:idx2] = ids
                schools_dset["n_pupils_max"].resize(newshape)
                schools_dset["n_pupils_max"][idx1:idx2] = n_pupils_max
                schools_dset["age_min"].resize(newshape)
                schools_dset["age_min"][idx1:idx2] = age_min
                schools_dset["age_max"].resize(newshape)
                schools_dset["age_max"][idx1:idx2] = age_max
                schools_dset["sector"].resize(newshape)
                schools_dset["sector"][idx1:idx2] = sectors
                schools_dset["coordinates"].resize(newshape[0], axis=0)
                schools_dset["coordinates"][idx1:idx2] = coordinates
                schools_dset["area"].resize(newshape[0], axis=0)
                schools_dset["area"][idx1:idx2] = areas
                schools_dset["n_classrooms"].resize(newshape[0], axis=0)
                schools_dset["n_classrooms"][idx1:idx2] = n_classrooms 
                schools_dset["years"].resize(newshape[0], axis=0)
                schools_dset["years"][idx1:idx2] = years 




def load_schools_from_hdf5(file_path: str, chunk_size: int = 50000):
    """
    Loads schools from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        schools = f["schools"]
        schools_list = []
        n_schools = schools.attrs["n_schools"]
        n_chunks = int(np.ceil(n_schools / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_schools)
            length = idx2 - idx1
            ids = np.empty(length, dtype=int)
            schools["id"].read_direct(ids, np.s_[idx1:idx2], np.s_[0:length])
            n_pupils_max = np.empty(length, dtype=int)
            schools["n_pupils_max"].read_direct(
                n_pupils_max, np.s_[idx1:idx2], np.s_[0:length]
            )
            age_min = np.empty(length, dtype=int)
            schools["age_min"].read_direct(age_min, np.s_[idx1:idx2], np.s_[0:length])
            age_max = np.empty(length, dtype=int)
            schools["age_max"].read_direct(age_max, np.s_[idx1:idx2], np.s_[0:length])
            coordinates = np.empty((length,2), dtype=float)
            schools["coordinates"].read_direct(
                coordinates, np.s_[idx1:idx2], np.s_[0:length]
            )
            n_classrooms= np.empty(length, dtype=int)
            schools["n_classrooms"].read_direct(
                n_classrooms, np.s_[idx1:idx2], np.s_[0:length]
            )
            years = np.empty(length, dtype=int_vlen_type)
            schools["years"].read_direct(
                years, np.s_[idx1:idx2], np.s_[0:length]
            )

            sectors = np.empty(length, dtype="S20")
            schools["sector"].read_direct(sectors, np.s_[idx1:idx2], np.s_[0:length])
            for k in range(idx2 - idx1):
                sector = sectors[k]
                if sector.decode() == " ":
                    sector = None
                else:
                    sector = sector.decode()
                school = School(
                    coordinates=coordinates[k],
                    n_pupils_max=n_pupils_max[k],
                    age_min=age_min[k],
                    age_max=age_max[k],
                    sector=sector,
                    n_classrooms=n_classrooms[k],
                    years=years[k],
                )
                school.id = ids[k]
                schools_list.append(school)
    return Schools(schools_list)

def restore_school_properties_from_hdf5(world: World, file_path: str, chunk_size):
    first_school_id = world.schools[0].id
    first_area_id = world.areas[0].id
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        schools = f["schools"]
        schools_list = []
        n_schools = schools.attrs["n_schools"]
        n_chunks = int(np.ceil(n_schools / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_schools)
            length = idx2 - idx1
            ids = np.empty(length, dtype=int)
            schools["id"].read_direct(ids, np.s_[idx1:idx2], np.s_[0:length])
            areas = np.empty(length, dtype=int)
            schools["area"].read_direct(areas, np.s_[idx1:idx2], np.s_[0:length])
            for k in range(length):
                school = world.schools[ids[k] - first_school_id]
                area = areas[k]
                if area == nan_integer:
                    school.area = None
                else:
                    school.area = world.areas[area - first_area_id]

