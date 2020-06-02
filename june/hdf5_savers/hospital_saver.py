import h5py
import numpy as np
from june.groups import Hospital, Hospitals 

nan_integer = -999

def save_hospitals_to_hdf5(
    hospitals: Hospitals, file_path: str, chunk_size: int = 50000
):
    """
    Saves the Hospitals object to hdf5 format file ``file_path``. Currently for each person,
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
    n_hospitals = len(hospitals)
    n_chunks = int(np.ceil(n_hospitals/ chunk_size))
    vlen_type = h5py.vlen_dtype(np.dtype("float64"))
    with h5py.File(file_path, "a") as f:
        hospitals_dset = f.create_group("hospitals")
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_hospitals)
            ids = []
            n_beds = []
            n_icu_beds = []
            super_areas = []
            coordinates = []
            contact_matrices_sizes = []
            contact_matrices_contacts = []
            contact_matrices_physical = []
            for hospital in hospitals[idx1:idx2]:
                ids.append(hospital.id)
                if hospital.super_area is None:
                    super_areas.append(nan_integer)
                else:
                    super_areas.append(hospital.super_area.id)
                n_beds.append(hospital.n_beds)
                n_icu_beds.append(hospital.n_icu_beds)
                coordinates.append(np.array(hospital.coordinates))
                contact_matrices_sizes.append(hospital.contact_matrices["contacts"].shape)
                contact_matrices_contacts.append(
                    hospital.contact_matrices["contacts"].flatten()
                )
                contact_matrices_physical.append(
                    hospital.contact_matrices["proportion_physical"].flatten()
                )

            ids = np.array(ids, dtype=np.int)
            super_areas = np.array(super_areas, dtype=np.int)
            n_beds = np.array(n_beds, dtype=np.int)
            n_icu_beds = np.array(n_icu_beds, dtype=np.int)
            coordinates = np.array(coordinates, dtype=np.float)
            contact_matrices_size = np.array(contact_matrices_sizes, dtype=np.int)
            contact_matrices_contacts = np.array(
                contact_matrices_contacts,
            )
            contact_matrices_physical = np.array(
                contact_matrices_physical,
            )
            if chunk == 0:
                hospitals_dset.attrs["n_hospitals"] = n_hospitals
                hospitals_dset.create_dataset("id", data=ids, maxshape=(None,))
                hospitals_dset.create_dataset("super_area", data=super_areas, maxshape=(None,))
                hospitals_dset.create_dataset("n_beds", data=n_beds, maxshape=(None,))
                hospitals_dset.create_dataset("n_icu_beds", data=n_icu_beds, maxshape=(None,))
                hospitals_dset.create_dataset("coordinates", data=coordinates, maxshape=(None, coordinates.shape[1]))
                hospitals_dset.create_dataset(
                    "contact_matrices_size",
                    data=contact_matrices_size,
                    maxshape=(None, contact_matrices_size.shape[1]),
                ),
                hospitals_dset.create_dataset(
                    "contact_matrices_contacts",
                    data=contact_matrices_contacts,
                    maxshape=(None, contact_matrices_contacts.shape[1]),
                )
                hospitals_dset.create_dataset(
                    "contact_matrices_physical",
                    data=contact_matrices_physical,
                    maxshape=(None, contact_matrices_physical.shape[1]),
                )
            else:
                newshape = (hospitals_dset["id"].shape[0] + ids.shape[0],)
                hospitals_dset["id"].resize(newshape)
                hospitals_dset["id"][idx1:idx2] = ids
                hospitals_dset["super_area"].resize(newshape)
                hospitals_dset["super_area"][idx1:idx2] = super_areas
                hospitals_dset["n_beds"].resize(newshape)
                hospitals_dset["n_beds"][idx1:idx2] = n_beds
                hospitals_dset["n_icu_beds"].resize(newshape)
                hospitals_dset["n_icu_beds"][idx1:idx2] = n_icu_beds
                hospitals_dset["coordinates"].resize(newshape[0], axis=0)
                hospitals_dset["coordinates"][idx1:idx2] = coordinates
                hospitals_dset["contact_matrices_size"].resize(newshape[0], axis=0)
                hospitals_dset["contact_matrices_size"][idx1:idx2] = contact_matrices_size 
                hospitals_dset["contact_matrices_contacts"].resize(newshape[0], axis=0)
                hospitals_dset["contact_matrices_contacts"][
                    idx1:idx2
                ] = contact_matrices_contacts
                hospitals_dset["contact_matrices_physical"].resize(newshape[0], axis=0)
                hospitals_dset["contact_matrices_physical"][
                    idx1:idx2
                ] = contact_matrices_physical


def load_hospitals_from_hdf5(file_path: str, chunk_size=50000):
    """
    Loads companies from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r") as f:
        hospitals = f["hospitals"]
        hospitals_list = list()
        chunk_size = 50000
        n_hospitals = hospitals.attrs["n_hospitals"]
        n_chunks = int(np.ceil(n_hospitals / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_hospitals)
            ids = hospitals["id"][idx1:idx2]
            super_areas = hospitals["super_area"][idx1:idx2]
            n_beds_list = hospitals["n_beds"][idx1:idx2]
            n_icu_beds_list = hospitals["n_icu_beds"][idx1:idx2]
            coordinates = hospitals["coordinates"][idx1:idx2]
            contact_matrices_size = hospitals["contact_matrices_size"][idx1:idx2]
            contact_matrices_contacts = hospitals["contact_matrices_contacts"][idx1:idx2]
            contact_matrices_physical = hospitals["contact_matrices_physical"][idx1:idx2]
            for k in range(idx2 - idx1):
                super_area = super_areas[k]
                if super_area == nan_integer:
                    super_area = None
                hospital = Hospital(
                    n_beds_list[k], n_icu_beds_list[k], super_area, coordinates[k]
                )
                hospital.contact_matrices = {
                    "contacts": contact_matrices_contacts[k].reshape(contact_matrices_size[k]),
                    "proportion_physical": contact_matrices_physical[k].reshape(contact_matrices_size[k]),
                }
                hospital.id = ids[k]
                hospitals_list.append(hospital)
    return Hospitals(hospitals_list)
