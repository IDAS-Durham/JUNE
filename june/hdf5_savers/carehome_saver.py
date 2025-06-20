import h5py
import numpy as np

from june.global_context import GlobalContext
from june.groups import CareHome, CareHomes
from june.world import World
from june.groups.group.make_subgroups import SubgroupParams
from .utils import read_dataset

nan_integer = -999


def save_care_homes_to_hdf5(
    care_homes: CareHomes, file_path: str, chunk_size: int = 50000
):
    """
    Saves the care_homes object to hdf5 format file ``file_path``. Currently for each care home,
    the following values are stored:
    - id, area, super_area, n_residents, n_workers, registered_members_ids

    Parameters
    ----------
    care_homes
        CareHomes object containing care home instances
    file_path
        path of the saved hdf5 file
    chunk_size
        number of care homes to save at a time. Note that they have to be copied to be saved,
        so keep the number below 1e6.
    """
    n_care_homes = len(care_homes)
    n_chunks = int(np.ceil(n_care_homes / chunk_size))
    with h5py.File(file_path, "a") as f:
        care_homes_dset = f.create_group("care_homes")
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_care_homes)
            ids = []
            areas = []
            super_areas = []
            n_residents = []
            n_workers = []
            registered_members_ids = []  # Add for storing registered_members_ids
            for carehome in care_homes[idx1:idx2]:
                ids.append(carehome.id)
                if carehome.area is None:
                    areas.append(nan_integer)
                    super_areas.append(nan_integer)
                else:
                    areas.append(carehome.area.id)
                    super_areas.append(carehome.super_area.id)
                n_residents.append(carehome.n_residents)
                n_workers.append(carehome.n_workers)
                
                # Process registered_members_ids
                carehome_registered_members = {}
                if hasattr(carehome, 'registered_members_ids') and carehome.registered_members_ids is not None:
                    for subgroup_id, members in carehome.registered_members_ids.items():
                        carehome_registered_members[subgroup_id] = np.array(members, dtype=np.int64)
                registered_members_ids.append(carehome_registered_members)

            ids = np.array(ids, dtype=np.int64)
            areas = np.array(areas, dtype=np.int64)
            n_residents = np.array(n_residents, dtype=np.float64)
            n_workers = np.array(n_workers, dtype=np.float64)
            
            # Create datasets to store registered_members_ids
            # First, determine what subgroups exist across all care homes
            all_subgroups = set()
            for ch_subgroups in registered_members_ids:
                all_subgroups.update(ch_subgroups.keys())
            all_subgroups = sorted(list(all_subgroups))  # Ensure consistent ordering
            
            # Store subgroup IDs as integers
            subgroup_ids = np.array(all_subgroups, dtype=np.int64)
            
            # Create counts and flattened arrays for each subgroup
            subgroup_counts = {}
            flattened_subgroup_members = {}
            
            for subgroup_id in all_subgroups:
                # Count of members in this subgroup for each care home
                counts = np.array([len(ch_dict.get(subgroup_id, [])) for ch_dict in registered_members_ids], dtype=np.int64)
                subgroup_counts[subgroup_id] = counts
                
                # Flatten all member IDs for this subgroup
                member_arrays = [ch_dict.get(subgroup_id, np.array([], dtype=np.int64)) for ch_dict in registered_members_ids]
                flattened = np.concatenate(member_arrays) if any(len(arr) > 0 for arr in member_arrays) else np.array([], dtype=np.int64)
                flattened_subgroup_members[subgroup_id] = flattened
            if chunk == 0:
                care_homes_dset.attrs["n_care_homes"] = n_care_homes
                care_homes_dset.create_dataset("id", data=ids, maxshape=(None,))
                care_homes_dset.create_dataset("area", data=areas, maxshape=(None,))
                care_homes_dset.create_dataset(
                    "super_area", data=super_areas, maxshape=(None,)
                )
                care_homes_dset.create_dataset(
                    "n_residents", data=n_residents, maxshape=(None,)
                )
                care_homes_dset.create_dataset(
                    "n_workers", data=n_workers, maxshape=(None,)
                )
                
                # Store registered_members_ids subgroups information
                if all_subgroups:  # Only create these datasets if we have subgroups
                    care_homes_dset.create_dataset("registered_members_subgroups", data=subgroup_ids, maxshape=(None,))
                    
                    # Create datasets for each subgroup
                    for subgroup_id in all_subgroups:
                        # Store counts for this subgroup
                        care_homes_dset.create_dataset(
                            f"registered_members_count_sg{subgroup_id}", 
                            data=subgroup_counts[subgroup_id], 
                            maxshape=(None,)
                        )
                        
                        # Store flattened members for this subgroup
                        flattened_members = flattened_subgroup_members[subgroup_id]
                        care_homes_dset.create_dataset(
                            f"registered_members_ids_sg{subgroup_id}", 
                            data=flattened_members, 
                            maxshape=(None,)
                        )
            else:
                newshape = (care_homes_dset["id"].shape[0] + ids.shape[0],)
                care_homes_dset["id"].resize(newshape)
                care_homes_dset["id"][idx1:idx2] = ids
                care_homes_dset["area"].resize(newshape)
                care_homes_dset["area"][idx1:idx2] = areas
                care_homes_dset["super_area"].resize(newshape)
                care_homes_dset["super_area"][idx1:idx2] = super_areas
                care_homes_dset["n_residents"].resize(newshape)
                care_homes_dset["n_residents"][idx1:idx2] = n_residents
                care_homes_dset["n_workers"].resize(newshape)
                care_homes_dset["n_workers"][idx1:idx2] = n_workers
                
                # Update registered members for subgroups
                if all_subgroups:  # Only update these datasets if we have subgroups
                    for subgroup_id in all_subgroups:
                        # Update counts for this subgroup
                        count_dataset = care_homes_dset[f"registered_members_count_sg{subgroup_id}"]
                        count_dataset.resize(newshape)
                        count_dataset[idx1:idx2] = subgroup_counts[subgroup_id]
                        
                        # Update flattened IDs for this subgroup (variable length)
                        ids_dataset = care_homes_dset[f"registered_members_ids_sg{subgroup_id}"]
                        flattened_members = flattened_subgroup_members[subgroup_id]
                        
                        if flattened_members.shape[0] > 0:
                            current_length = ids_dataset.shape[0]
                            new_length = current_length + flattened_members.shape[0]
                            ids_dataset.resize((new_length,))
                            ids_dataset[current_length:new_length] = flattened_members


def load_care_homes_from_hdf5(
    file_path: str, chunk_size=50000, domain_super_areas=None, config_filename=None
):
    """
    Loads carehomes from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    CareHome_Class = CareHome
    disease_config = GlobalContext.get_disease_config()
    CareHome_Class.subgroup_params = SubgroupParams.from_disease_config(disease_config)

    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        care_homes = f["care_homes"]
        care_homes_list = []
        n_carehomes = care_homes.attrs["n_care_homes"]
        n_chunks = int(np.ceil(n_carehomes / chunk_size))
        
        # Check if registered members data exists
        has_subgroup_data = "registered_members_subgroups" in care_homes
        subgroup_counts = {}
        subgroup_members = {}
        subgroup_cumulative_counts = {}
        
        if has_subgroup_data:
            # Get all subgroups
            subgroups = read_dataset(care_homes["registered_members_subgroups"], 0, care_homes["registered_members_subgroups"].shape[0])
            
            # For each subgroup, prepare the count and flattened arrays
            for subgroup_id in subgroups:
                sg_key = f"registered_members_count_sg{subgroup_id}"
                ids_key = f"registered_members_ids_sg{subgroup_id}"
                
                if sg_key in care_homes and ids_key in care_homes:
                    # Read counts for this subgroup
                    counts = read_dataset(care_homes[sg_key], 0, n_carehomes)
                    subgroup_counts[subgroup_id] = counts
                    
                    # Calculate cumulative counts for this subgroup
                    cumulative = np.concatenate(([0], np.cumsum(counts)))
                    subgroup_cumulative_counts[subgroup_id] = cumulative
                    
                    # Read flattened member IDs for this subgroup
                    if care_homes[ids_key].shape[0] > 0:
                        member_ids = read_dataset(care_homes[ids_key], 0, care_homes[ids_key].shape[0])
                        subgroup_members[subgroup_id] = member_ids
                    else:
                        subgroup_members[subgroup_id] = np.array([])
        
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_carehomes)
            ids = read_dataset(care_homes["id"], idx1, idx2)
            n_residents = read_dataset(care_homes["n_residents"], idx1, idx2)
            n_workers = read_dataset(care_homes["n_workers"], idx1, idx2)
            super_areas = read_dataset(care_homes["super_area"], idx1, idx2)
            for k in range(idx2 - idx1):
                if domain_super_areas is not None:
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                
                # Get registered_members_ids for this care home if available
                registered_members_dict = {}
                
                if has_subgroup_data and subgroups.size > 0:
                    care_home_index = idx1 + k
                    
                    # Get members for each subgroup
                    for subgroup_id in subgroups:
                        if subgroup_id in subgroup_counts and subgroup_id in subgroup_members:
                            n_members = subgroup_counts[subgroup_id][care_home_index]
                            
                            if n_members > 0 and len(subgroup_members[subgroup_id]) > 0:
                                start_idx = subgroup_cumulative_counts[subgroup_id][care_home_index]
                                end_idx = subgroup_cumulative_counts[subgroup_id][care_home_index + 1]
                                
                                if start_idx < len(subgroup_members[subgroup_id]):
                                    registered_members_dict[int(subgroup_id)] = subgroup_members[subgroup_id][start_idx:end_idx].tolist()
                
                care_home = CareHome_Class(
                    area=None, n_residents=n_residents[k], n_workers=n_workers[k],
                    registered_members_ids=registered_members_dict
                )
                care_home.id = ids[k]
                care_homes_list.append(care_home)
    return CareHomes(care_homes_list)


def restore_care_homes_properties_from_hdf5(
    world: World, file_path: str, chunk_size=50000, domain_super_areas=None
):
    """
    Loads carehomes from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        carehomes = f["care_homes"]
        n_carehomes = carehomes.attrs["n_care_homes"]
        n_chunks = int(np.ceil(n_carehomes / chunk_size))
        
        # Check if registered members data exists
        has_subgroup_data = "registered_members_subgroups" in carehomes
        subgroup_counts = {}
        subgroup_members = {}
        subgroup_cumulative_counts = {}
        
        if has_subgroup_data:
            # Get all subgroups
            subgroups = read_dataset(carehomes["registered_members_subgroups"], 0, carehomes["registered_members_subgroups"].shape[0])
            
            # For each subgroup, prepare the count and flattened arrays
            for subgroup_id in subgroups:
                sg_key = f"registered_members_count_sg{subgroup_id}"
                ids_key = f"registered_members_ids_sg{subgroup_id}"
                
                if sg_key in carehomes and ids_key in carehomes:
                    # Read counts for this subgroup
                    counts = read_dataset(carehomes[sg_key], 0, n_carehomes)
                    subgroup_counts[subgroup_id] = counts
                    
                    # Calculate cumulative counts for this subgroup
                    cumulative = np.concatenate(([0], np.cumsum(counts)))
                    subgroup_cumulative_counts[subgroup_id] = cumulative
                    
                    # Read flattened member IDs for this subgroup
                    if carehomes[ids_key].shape[0] > 0:
                        member_ids = read_dataset(carehomes[ids_key], 0, carehomes[ids_key].shape[0])
                        subgroup_members[subgroup_id] = member_ids
                    else:
                        subgroup_members[subgroup_id] = np.array([])
        
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_carehomes)
            ids = carehomes["id"][idx1:idx2]
            areas = carehomes["area"][idx1:idx2]
            super_areas = carehomes["super_area"][idx1:idx2]
            for k in range(idx2 - idx1):
                if domain_super_areas is not None:
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                care_home = world.care_homes.get_from_id(ids[k])
                if areas[k] == nan_integer:
                    area = None
                else:
                    area = world.areas.get_from_id(areas[k])
                care_home.area = area
                if area is not None:
                    area.care_home = care_home
                
                # Restore registered_members_ids if available
                if has_subgroup_data and subgroups.size > 0:
                    care_home_index = idx1 + k
                    registered_members_dict = {}
                    
                    # Process each subgroup
                    for subgroup_id in subgroups:
                        if subgroup_id in subgroup_counts and subgroup_id in subgroup_members:
                            n_members = subgroup_counts[subgroup_id][care_home_index]
                            
                            if n_members > 0 and len(subgroup_members[subgroup_id]) > 0:
                                start_idx = subgroup_cumulative_counts[subgroup_id][care_home_index]
                                end_idx = subgroup_cumulative_counts[subgroup_id][care_home_index + 1]
                                
                                if start_idx < len(subgroup_members[subgroup_id]):
                                    registered_members_dict[int(subgroup_id)] = subgroup_members[subgroup_id][start_idx:end_idx].tolist()
                    
                    # Update the registered_members_ids with the data loaded from file
                    care_home.registered_members_ids = registered_members_dict
