import h5py
import numpy as np

from june.world import World
from june.groups import Hospital, Hospitals, ExternalHospital
from .utils import read_dataset

nan_integer = -999


def save_hospitals_to_hdf5(
    hospitals: Hospitals, file_path: str, chunk_size: int = 50000
):
    """
    Saves the Hospitals object to hdf5 format file ``file_path``. Currently for each person,
    the following values are stored:
    - id, n_beds, n_icu_beds, area, coordinates

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
    n_hospitals = len(hospitals)
    n_chunks = int(np.ceil(n_hospitals / chunk_size))
    vlen_type = h5py.vlen_dtype(np.dtype("float64"))
    with h5py.File(file_path, "a") as f:
        hospitals_dset = f.create_group("hospitals")
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_hospitals)
            ids = []
            n_beds = []
            n_icu_beds = []
            areas = []
            super_areas = []
            region_names = []
            coordinates = []
            trust_code = []
            for hospital in hospitals[idx1:idx2]:
                ids.append(hospital.id)
                if hospital.area is None:
                    areas.append(nan_integer)
                    super_areas.append(nan_integer)
                    region_names.append(nan_integer)
                else:
                    areas.append(hospital.area.id)
                    super_areas.append(hospital.super_area.id)
                    region_names.append(hospital.region_name)
                n_beds.append(hospital.n_beds)
                n_icu_beds.append(hospital.n_icu_beds)
                coordinates.append(np.array(hospital.coordinates))
                trust_code.append(hospital.trust_code)

            ids = np.array(ids, dtype=np.int64)
            areas = np.array(areas, dtype=np.int64)
            super_areas = np.array(super_areas, dtype=np.int64)
            region_names = np.array(region_names, dtype="S50")
            trust_code = np.array(trust_code, dtype="S10")
            n_beds = np.array(n_beds, dtype=np.int64)
            n_icu_beds = np.array(n_icu_beds, dtype=np.int64)
            coordinates = np.array(coordinates, dtype=np.float64)
            if chunk == 0:
                hospitals_dset.attrs["n_hospitals"] = n_hospitals
                hospitals_dset.create_dataset("id", data=ids, maxshape=(None,))
                hospitals_dset.create_dataset("area", data=areas, maxshape=(None,))
                hospitals_dset.create_dataset(
                    "super_area", data=super_areas, maxshape=(None,)
                )
                hospitals_dset.create_dataset(
                    "region_name", data=region_names, maxshape=(None,)
                )
                hospitals_dset.create_dataset(
                    "trust_code", data=trust_code, maxshape=(None,)
                )
                hospitals_dset.create_dataset("n_beds", data=n_beds, maxshape=(None,))
                hospitals_dset.create_dataset(
                    "n_icu_beds", data=n_icu_beds, maxshape=(None,)
                )
                hospitals_dset.create_dataset(
                    "coordinates",
                    data=coordinates,
                    maxshape=(None, coordinates.shape[1]),
                )
            else:
                newshape = (hospitals_dset["id"].shape[0] + ids.shape[0],)
                hospitals_dset["id"].resize(newshape)
                hospitals_dset["id"][idx1:idx2] = ids
                hospitals_dset["area"].resize(newshape)
                hospitals_dset["area"][idx1:idx2] = areas
                hospitals_dset["super_area"].resize(newshape)
                hospitals_dset["super_area"][idx1:idx2] = super_areas
                hospitals_dset["region_name"].resize(newshape)
                hospitals_dset["region_name"][idx1:idx2] = region_names
                hospitals_dset["trust_code"].resize(newshape)
                hospitals_dset["trust_code"][idx1:idx2] = trust_code
                hospitals_dset["n_beds"].resize(newshape)
                hospitals_dset["n_beds"][idx1:idx2] = n_beds
                hospitals_dset["n_icu_beds"].resize(newshape)
                hospitals_dset["n_icu_beds"][idx1:idx2] = n_icu_beds
                hospitals_dset["coordinates"].resize(newshape[0], axis=0)
                hospitals_dset["coordinates"][idx1:idx2] = coordinates


def load_hospitals_from_hdf5(
    file_path: str,
    chunk_size=50000,
    domain_super_areas=None,
    super_areas_to_domain_dict: dict = None,
):
    """
    Loads companies from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        hospitals = f["hospitals"]
        hospitals_list = []
        chunk_size = 50000
        n_hospitals = hospitals.attrs["n_hospitals"]
        n_chunks = int(np.ceil(n_hospitals / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_hospitals)
            length = idx2 - idx1
            ids = read_dataset(hospitals["id"], idx1, idx2)
            n_beds_list = read_dataset(hospitals["n_beds"], idx1, idx2)
            n_icu_beds_list = read_dataset(hospitals["n_icu_beds"], idx1, idx2)
            trust_codes = read_dataset(hospitals["trust_code"], idx1, idx2)
            coordinates = read_dataset(hospitals["coordinates"], idx1, idx2)
            areas = read_dataset(hospitals["area"], idx1, idx2)
            super_areas = read_dataset(hospitals["super_area"], idx1, idx2)
            region_name = read_dataset(hospitals["region_name"], idx1, idx2)
            for k in range(idx2 - idx1):
                super_area = super_areas[k]
                if super_area == nan_integer:
                    raise ValueError(
                        "if ``domain_super_areas`` is True, I expect not Nones super areas."
                    )
                trust_code = trust_codes[k]
                if trust_code.decode() == " ":
                    trust_code = None
                else:
                    trust_code = trust_code.decode()

                if (
                    domain_super_areas is not None
                    and super_area not in domain_super_areas
                ):
                    hospital = ExternalHospital(
                        id=ids[k],
                        spec="hospital",
                        domain_id=super_areas_to_domain_dict[super_area],
                        region_name=region_name[k].decode(),
                    )
                else:
                    hospital = Hospital(
                        n_beds=n_beds_list[k],
                        n_icu_beds=n_icu_beds_list[k],
                        coordinates=coordinates[k],
                        trust_code=trust_code,
                    )
                    hospital.id = ids[k]
                hospitals_list.append(hospital)
    return Hospitals(hospitals_list, ball_tree=False)


def restore_hospital_properties_from_hdf5(
    world: World,
    file_path: str,
    chunk_size=50000,
    domain_super_areas=None,
    domain_areas=None,
    super_areas_to_domain_dict: dict = None,
):
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        hospitals = f["hospitals"]
        hospitals_list = []
        n_hospitals = hospitals.attrs["n_hospitals"]
        n_chunks = int(np.ceil(n_hospitals / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_hospitals)
            length = idx2 - idx1
            ids = np.empty(length, dtype=int)
            hospitals["id"].read_direct(ids, np.s_[idx1:idx2], np.s_[0:length])
            areas = np.empty(length, dtype=int)
            hospitals["area"].read_direct(areas, np.s_[idx1:idx2], np.s_[0:length])
            for k in range(length):
                if domain_areas is not None:
                    area = areas[k]
                    if area == nan_integer:
                        raise ValueError(
                            "if ``domain_areas`` is True, I expect not Nones areas."
                        )
                    if area not in domain_areas:
                        continue
                hospital = world.hospitals.get_from_id(ids[k])
                area = areas[k]
                if area == nan_integer:
                    area = None
                else:
                    area = world.areas.get_from_id(area)
                hospital.area = area

        # super areas
        geography = f["geography"]
        n_super_areas = geography.attrs["n_super_areas"]
        n_chunks = int(np.ceil(n_super_areas / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_super_areas)
            length = idx2 - idx1
            super_areas_ids = read_dataset(geography["super_area_id"], idx1, idx2)
            closest_hospitals_ids = read_dataset(
                geography["closest_hospitals_ids"], idx1, idx2
            )
            closest_hospitals_super_areas = read_dataset(
                geography["closest_hospitals_super_areas"], idx1, idx2
            )
            for k in range(length):
                if domain_super_areas is not None:
                    super_area_id = super_areas_ids[k]
                    if super_area_id == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super_areas."
                        )
                    if super_area_id not in domain_super_areas:
                        continue
                super_area = world.super_areas.get_from_id(super_areas_ids[k])
                # load closest hospitals
                hospitals = []
                for hospital_id, hospital_super_area_id in zip(
                    closest_hospitals_ids[k], closest_hospitals_super_areas[k]
                ):
                    hospital = world.hospitals.get_from_id(hospital_id)
                    hospitals.append(hospital)
                super_area.closest_hospitals = hospitals
