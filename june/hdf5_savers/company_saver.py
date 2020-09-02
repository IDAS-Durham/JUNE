import h5py
import numpy as np

from june.groups import Company, Companies
from june.world import World

nan_integer = -999


def save_companies_to_hdf5(
    companies: Companies, file_path: str, chunk_size: int = 500000
):
    """
    Saves the Population object to hdf5 format file ``file_path``. Currently for each person,
    the following values are stored:
    - id, super_area, sector, n_workers_max, 

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
    n_companies = len(companies)
    n_chunks = int(np.ceil(n_companies / chunk_size))
    vlen_type = h5py.vlen_dtype(np.dtype("float64"))
    with h5py.File(file_path, "a") as f:
        companies_dset = f.create_group("companies")
        first_company_idx = companies[0].id
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_companies)
            ids = []
            super_areas = []
            sectors = []
            n_workers_max = []
            company_idx = [company.id for company in companies[idx1:idx2]]
            # sort companies by id
            companies_sorted = [
                companies[i - first_company_idx] for i in np.sort(company_idx)
            ]
            for company in companies_sorted:
                ids.append(company.id)
                if company.super_area is None:
                    super_areas.append(nan_integer)
                else:
                    super_areas.append(company.super_area.id)
                sectors.append(company.sector.encode("ascii", "ignore"))
                n_workers_max.append(company.n_workers_max)

            ids = np.array(ids, dtype=np.int)
            super_areas = np.array(super_areas, dtype=np.int)
            sectors = np.array(sectors, dtype="S10")
            n_workers_max = np.array(n_workers_max, dtype=np.float)
            if chunk == 0:
                companies_dset.attrs["n_companies"] = n_companies
                companies_dset.create_dataset("id", data=ids, maxshape=(None,))
                companies_dset.create_dataset(
                    "super_area", data=super_areas, maxshape=(None,)
                )
                companies_dset.create_dataset("sector", data=sectors, maxshape=(None,))
                companies_dset.create_dataset(
                    "n_workers_max", data=n_workers_max, maxshape=(None,)
                )
            else:
                newshape = (companies_dset["id"].shape[0] + ids.shape[0],)
                companies_dset["id"].resize(newshape)
                companies_dset["id"][idx1:idx2] = ids
                companies_dset["super_area"].resize(newshape)
                companies_dset["super_area"][idx1:idx2] = super_areas
                companies_dset["sector"].resize(newshape)
                companies_dset["sector"][idx1:idx2] = sectors
                companies_dset["n_workers_max"].resize(newshape)
                companies_dset["n_workers_max"][idx1:idx2] = n_workers_max


def load_companies_from_hdf5(file_path: str, chunk_size=50000):
    """
    Loads companies from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        companies = f["companies"]
        companies_list = []
        n_companies = companies.attrs["n_companies"]
        n_chunks = int(np.ceil(n_companies / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_companies)
            length = idx2 - idx1
            ids = np.empty(length, dtype=int)
            companies["id"].read_direct(ids, np.s_[idx1:idx2], np.s_[0:length])
            sectors = np.empty(length, dtype="S20")
            companies["sector"].read_direct(sectors, np.s_[idx1:idx2], np.s_[0:length])
            n_workers_maxs = np.empty(length, dtype=int)
            companies["n_workers_max"].read_direct(
                n_workers_maxs, np.s_[idx1:idx2], np.s_[0:length]
            )
            for k in range(length):
                company = Company(
                    super_area=None,
                    n_workers_max=n_workers_maxs[k],
                    sector=sectors[k].decode(),
                )
                company.id = ids[k]
                companies_list.append(company)
    return Companies(companies_list)


def restore_companies_properties_from_hdf5(world: World, file_path: str, chunk_size):
    super_areas_first_id = world.super_areas[
        0
    ].id  # in case some super areas were created before
    first_company_id = world.companies[0].id
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        companies = f["companies"]
        companies_list = []
        n_companies = companies.attrs["n_companies"]
        n_chunks = int(np.ceil(n_companies / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_companies)
            length = idx2 - idx1
            ids = np.empty(length, dtype=int)
            companies["id"].read_direct(ids, np.s_[idx1:idx2], np.s_[0:length])
            super_areas = np.empty(length, dtype=int)
            companies["super_area"].read_direct(
                super_areas, np.s_[idx1:idx2], np.s_[0:length]
            )
            for k in range(length):
                company = world.companies[ids[k] - first_company_id]
                if super_areas[k] == nan_integer:
                    company.super_area = None
                else:
                    company.super_area = world.super_areas[
                        super_areas[k] - super_areas_first_id
                    ]
