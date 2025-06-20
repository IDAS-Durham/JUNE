import h5py
import numpy as np
import logging

from june.global_context import GlobalContext
from june.groups import Company, Companies
from june.world import World
from june.groups.group.make_subgroups import SubgroupParams
from june.mpi_wrapper import mpi_rank
from .utils import read_dataset

nan_integer = -999

logger = logging.getLogger("company_saver")
if mpi_rank > 0:
    logger.propagate = False


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
            registered_members_ids = []  # Add new list for registered_members_ids
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
                # Handle registered_members_ids - always a dictionary with subgroups
                if hasattr(company, 'registered_members_ids') and company.registered_members_ids is not None:
                    subgroup_dict = {}
                    for subgroup_id, members in company.registered_members_ids.items():
                        subgroup_dict[subgroup_id] = np.array(members, dtype=np.int64)
                    registered_members_ids.append(subgroup_dict)
                else:
                    registered_members_ids.append({})  # Empty dictionary

            ids = np.array(ids, dtype=np.int64)
            super_areas = np.array(super_areas, dtype=np.int64)
            sectors = np.array(sectors, dtype="S10")
            n_workers_max = np.array(n_workers_max, dtype=np.float64)
            
            # Create datasets to store the number of registered members per company per subgroup
            # First, determine what subgroups exist across all companies
            all_subgroups = set()
            for company_subgroups in registered_members_ids:
                all_subgroups.update(company_subgroups.keys())
            all_subgroups = sorted(list(all_subgroups))  # Ensure consistent ordering
            
            # Store subgroup IDs as integers
            subgroup_ids = np.array(all_subgroups, dtype=np.int64)
            
            # Create counts and flattened arrays for each subgroup
            subgroup_counts = {}
            flattened_subgroup_members = {}
            
            for subgroup_id in all_subgroups:
                # Count of members in this subgroup for each company
                counts = np.array([len(company_dict.get(subgroup_id, [])) for company_dict in registered_members_ids], dtype=np.int64)
                subgroup_counts[subgroup_id] = counts
                
                # Flatten all member IDs for this subgroup
                member_arrays = [company_dict.get(subgroup_id, np.array([], dtype=np.int64)) for company_dict in registered_members_ids]
                flattened = np.concatenate(member_arrays) if any(len(arr) > 0 for arr in member_arrays) else np.array([], dtype=np.int64)
                flattened_subgroup_members[subgroup_id] = flattened
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
                # Store registered_members_ids subgroups information
                # Store the subgroup IDs
                companies_dset.create_dataset("registered_members_subgroups", data=subgroup_ids, maxshape=(None,))
                
                # Create datasets for each subgroup
                for subgroup_id in all_subgroups:
                    # Store counts for this subgroup
                    companies_dset.create_dataset(
                        f"registered_members_count_sg{subgroup_id}", 
                        data=subgroup_counts[subgroup_id], 
                        maxshape=(None,)
                    )
                    
                    # Store flattened members for this subgroup
                    flattened_members = flattened_subgroup_members[subgroup_id]
                    companies_dset.create_dataset(
                        f"registered_members_ids_sg{subgroup_id}", 
                        data=flattened_members, 
                        maxshape=(None,)
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
                
                # Update registered members for subgroups
                for subgroup_id in all_subgroups:
                    # Update counts for this subgroup
                    count_dataset = companies_dset[f"registered_members_count_sg{subgroup_id}"]
                    count_dataset.resize(newshape)
                    count_dataset[idx1:idx2] = subgroup_counts[subgroup_id]
                    
                    # Update flattened IDs for this subgroup (variable length)
                    ids_dataset = companies_dset[f"registered_members_ids_sg{subgroup_id}"]
                    flattened_members = flattened_subgroup_members[subgroup_id]
                    
                    if flattened_members.shape[0] > 0:
                        current_length = ids_dataset.shape[0]
                        new_length = current_length + flattened_members.shape[0]
                        ids_dataset.resize((new_length,))
                        ids_dataset[current_length:new_length] = flattened_members


def load_companies_from_hdf5(
    file_path: str, chunk_size=50000, domain_super_areas=None, config_filename=None
):
    """
    Loads companies from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """

    Company_Class = Company
    disease_config = GlobalContext.get_disease_config()
    Company_Class.subgroup_params = SubgroupParams.from_disease_config(disease_config)

    logger.info("loading companies...")
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        companies = f["companies"]
        companies_list = []
        n_companies = companies.attrs["n_companies"]
        n_chunks = int(np.ceil(n_companies / chunk_size))
        
        # Check if subgroup registered members data exists
        has_subgroup_data = "registered_members_subgroups" in companies
        
        if has_subgroup_data:
            # Get all subgroups
            subgroups = read_dataset(companies["registered_members_subgroups"], 0, companies["registered_members_subgroups"].shape[0])
            
            # For each subgroup, prepare the count and flattened arrays
            subgroup_counts = {}
            subgroup_members = {}
            subgroup_cumulative_counts = {}
            
            for subgroup_id in subgroups:
                sg_key = f"registered_members_count_sg{subgroup_id}"
                ids_key = f"registered_members_ids_sg{subgroup_id}"
                
                if sg_key in companies and ids_key in companies:
                    # Read counts for this subgroup
                    counts = read_dataset(companies[sg_key], 0, n_companies)
                    subgroup_counts[subgroup_id] = counts
                    
                    # Calculate cumulative counts for this subgroup
                    cumulative = np.concatenate(([0], np.cumsum(counts)))
                    subgroup_cumulative_counts[subgroup_id] = cumulative
                    
                    # Read flattened member IDs for this subgroup
                    if companies[ids_key].shape[0] > 0:
                        member_ids = read_dataset(companies[ids_key], 0, companies[ids_key].shape[0])
                        subgroup_members[subgroup_id] = member_ids
                    else:
                        subgroup_members[subgroup_id] = np.array([])
        
        for chunk in range(n_chunks):
            logger.info(f"Companies chunk {chunk} of {n_chunks}")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_companies)
            length = idx2 - idx1
            ids = read_dataset(companies["id"], idx1, idx2)
            sectors = read_dataset(companies["sector"], idx1, idx2)
            n_workers_maxs = read_dataset(companies["n_workers_max"], idx1, idx2)
            super_areas = read_dataset(companies["super_area"], idx1, idx2)
            
            for k in range(length):
                if domain_super_areas is not None:
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                
                # Get registered_members_ids for this company
                registered_members_dict = {}
                
                if has_subgroup_data:
                    company_index = idx1 + k
                    
                    # Get members for each subgroup
                    for subgroup_id in subgroups:
                        if subgroup_id in subgroup_counts and subgroup_id in subgroup_members:
                            n_members = subgroup_counts[subgroup_id][company_index]
                            
                            if n_members > 0 and len(subgroup_members[subgroup_id]) > 0:
                                start_idx = subgroup_cumulative_counts[subgroup_id][company_index]
                                end_idx = subgroup_cumulative_counts[subgroup_id][company_index + 1]
                                
                                if start_idx < len(subgroup_members[subgroup_id]):
                                    registered_members_dict[int(subgroup_id)] = subgroup_members[subgroup_id][start_idx:end_idx].tolist()
                
                company = Company(
                    super_area=None,
                    n_workers_max=n_workers_maxs[k],
                    sector=sectors[k].decode(),
                    registered_members_ids=registered_members_dict,
                )
                company.id = ids[k]
                companies_list.append(company)
    return Companies(companies_list)


def restore_companies_properties_from_hdf5(
    world: World, file_path: str, chunk_size, domain_super_areas=None
):
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        companies = f["companies"]
        n_companies = companies.attrs["n_companies"]
        n_chunks = int(np.ceil(n_companies / chunk_size))
        
        # Check if subgroup registered members data exists
        has_subgroup_data = "registered_members_subgroups" in companies
        
        if has_subgroup_data:
            # Get all subgroups
            subgroups = read_dataset(companies["registered_members_subgroups"], 0, companies["registered_members_subgroups"].shape[0])
            
            # For each subgroup, prepare the count and flattened arrays
            subgroup_counts = {}
            subgroup_members = {}
            subgroup_cumulative_counts = {}
            
            for subgroup_id in subgroups:
                sg_key = f"registered_members_count_sg{subgroup_id}"
                ids_key = f"registered_members_ids_sg{subgroup_id}"
                
                if sg_key in companies and ids_key in companies:
                    # Read counts for this subgroup
                    counts = read_dataset(companies[sg_key], 0, n_companies)
                    subgroup_counts[subgroup_id] = counts
                    
                    # Calculate cumulative counts for this subgroup
                    cumulative = np.concatenate(([0], np.cumsum(counts)))
                    subgroup_cumulative_counts[subgroup_id] = cumulative
                    
                    # Read flattened member IDs for this subgroup
                    if companies[ids_key].shape[0] > 0:
                        member_ids = read_dataset(companies[ids_key], 0, companies[ids_key].shape[0])
                        subgroup_members[subgroup_id] = member_ids
                    else:
                        subgroup_members[subgroup_id] = np.array([])
        
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_companies)
            length = idx2 - idx1
            ids = read_dataset(companies["id"], idx1, idx2)
            super_areas = read_dataset(companies["super_area"], idx1, idx2)
            
            for k in range(length):
                if domain_super_areas is not None:
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                        
                company = world.companies.get_from_id(ids[k])
                
                if super_areas[k] == nan_integer:
                    company.super_area = None
                else:
                    company.super_area = world.super_areas.get_from_id(super_areas[k])
                # Restore registered_members_ids if available
                if has_subgroup_data:
                    company_index = idx1 + k
                    registered_members_dict = {}
                    
                    # Process each subgroup
                    for subgroup_id in subgroups:
                        if subgroup_id in subgroup_counts and subgroup_id in subgroup_members:
                            n_members = subgroup_counts[subgroup_id][company_index]
                            
                            if n_members > 0 and len(subgroup_members[subgroup_id]) > 0:
                                start_idx = subgroup_cumulative_counts[subgroup_id][company_index]
                                end_idx = subgroup_cumulative_counts[subgroup_id][company_index + 1]
                                
                                if start_idx < len(subgroup_members[subgroup_id]):
                                    registered_members_dict[int(subgroup_id)] = subgroup_members[subgroup_id][start_idx:end_idx].tolist()
                    
                    # Always use dictionary format
                    company.registered_members_ids = registered_members_dict
