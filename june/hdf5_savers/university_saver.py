import h5py
import numpy as np

from june.global_context import GlobalContext
from june.groups import University, Universities
from june.groups.group.make_subgroups import SubgroupParams
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
        registered_members_ids = []  # Add for storing registered_members_ids
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
                
            # Process registered_members_ids
            university_registered_members = {}
            if hasattr(university, 'registered_members_ids') and university.registered_members_ids is not None:
                for subgroup_id, members in university.registered_members_ids.items():
                    university_registered_members[subgroup_id] = np.array(members, dtype=np.int64)
            registered_members_ids.append(university_registered_members)

        ids = np.array(ids, dtype=np.int64)
        n_students_max = np.array(n_students_max, dtype=np.int64)
        n_years = np.array(n_years, dtype=np.int64)
        ukprns = np.array(ukprns, dtype=np.int64)
        areas = np.array(areas, dtype=np.int64)
        coordinates = np.array(coordinates, dtype=np.float64)
        
        # Create datasets to store registered_members_ids
        # First, determine what subgroups exist across all universities
        all_subgroups = set()
        for uni_subgroups in registered_members_ids:
            all_subgroups.update(uni_subgroups.keys())
        all_subgroups = sorted(list(all_subgroups))  # Ensure consistent ordering
        
        # Store subgroup IDs as integers
        subgroup_ids = np.array(all_subgroups, dtype=np.int64)
        
        # Create counts and flattened arrays for each subgroup
        subgroup_counts = {}
        flattened_subgroup_members = {}
        
        for subgroup_id in all_subgroups:
            # Count of members in this subgroup for each university
            counts = np.array([len(uni_dict.get(subgroup_id, [])) for uni_dict in registered_members_ids], dtype=np.int64)
            subgroup_counts[subgroup_id] = counts
            
            # Flatten all member IDs for this subgroup
            member_arrays = [uni_dict.get(subgroup_id, np.array([], dtype=np.int64)) for uni_dict in registered_members_ids]
            flattened = np.concatenate(member_arrays) if any(len(arr) > 0 for arr in member_arrays) else np.array([], dtype=np.int64)
            flattened_subgroup_members[subgroup_id] = flattened
        universities_dset.attrs["n_universities"] = n_universities
        universities_dset.create_dataset("id", data=ids)
        universities_dset.create_dataset("n_students_max", data=n_students_max)
        universities_dset.create_dataset("n_years", data=n_years)
        universities_dset.create_dataset("area", data=areas)
        universities_dset.create_dataset("coordinates", data=coordinates)
        universities_dset.create_dataset("ukprns", data=ukprns)
        
        # Store registered_members_ids subgroups information
        if all_subgroups:  # Only create these datasets if we have subgroups
            universities_dset.create_dataset("registered_members_subgroups", data=subgroup_ids, maxshape=(None,))
            
            # Create datasets for each subgroup
            for subgroup_id in all_subgroups:
                # Store counts for this subgroup
                universities_dset.create_dataset(
                    f"registered_members_count_sg{subgroup_id}", 
                    data=subgroup_counts[subgroup_id], 
                    maxshape=(None,)
                )
                
                # Store flattened members for this subgroup
                flattened_members = flattened_subgroup_members[subgroup_id]
                universities_dset.create_dataset(
                    f"registered_members_ids_sg{subgroup_id}", 
                    data=flattened_members, 
                    maxshape=(None,)
                )


def load_universities_from_hdf5(
    file_path: str, chunk_size: int = 50000, domain_areas=None, config_filename=None
):
    """
    Loads universities from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """

    University_Class = University
    disease_config = GlobalContext.get_disease_config()
    University_Class.subgroup_params = SubgroupParams.from_disease_config(disease_config)

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
        
        # Check if registered members data exists
        has_subgroup_data = "registered_members_subgroups" in universities
        subgroup_counts = {}
        subgroup_members = {}
        subgroup_cumulative_counts = {}
        
        if has_subgroup_data:
            # Get all subgroups
            subgroups = read_dataset(universities["registered_members_subgroups"], 0, universities["registered_members_subgroups"].shape[0])
            
            # For each subgroup, prepare the count and flattened arrays
            for subgroup_id in subgroups:
                sg_key = f"registered_members_count_sg{subgroup_id}"
                ids_key = f"registered_members_ids_sg{subgroup_id}"
                
                if sg_key in universities and ids_key in universities:
                    # Read counts for this subgroup
                    counts = read_dataset(universities[sg_key], 0, n_universities)
                    subgroup_counts[subgroup_id] = counts
                    
                    # Calculate cumulative counts for this subgroup
                    cumulative = np.concatenate(([0], np.cumsum(counts)))
                    subgroup_cumulative_counts[subgroup_id] = cumulative
                    
                    # Read flattened member IDs for this subgroup
                    if universities[ids_key].shape[0] > 0:
                        member_ids = read_dataset(universities[ids_key], 0, universities[ids_key].shape[0])
                        subgroup_members[subgroup_id] = member_ids
                    else:
                        subgroup_members[subgroup_id] = np.array([])
        for k in range(n_universities):
            if domain_areas is not None:
                area = areas[k]
                if area == nan_integer:
                    raise ValueError(
                        "if ``domain_areas`` is True, I expect not Nones areas."
                    )
                if area not in domain_areas:
                    continue
            
            # Get registered_members_ids for this university if available
            registered_members_dict = {}
            
            if has_subgroup_data and subgroups.size > 0:
                university_index = k
                
                # Get members for each subgroup
                for subgroup_id in subgroups:
                    if subgroup_id in subgroup_counts and subgroup_id in subgroup_members:
                        n_members = subgroup_counts[subgroup_id][university_index]
                        
                        if n_members > 0 and len(subgroup_members[subgroup_id]) > 0:
                            start_idx = subgroup_cumulative_counts[subgroup_id][university_index]
                            end_idx = subgroup_cumulative_counts[subgroup_id][university_index + 1]
                            
                            if start_idx < len(subgroup_members[subgroup_id]):
                                registered_members_dict[int(subgroup_id)] = subgroup_members[subgroup_id][start_idx:end_idx].tolist()
            
            university = University_Class(
                n_students_max=n_students_max[k],
                n_years=n_years[k],
                ukprn=ukprns[k],
                coordinates=coordinates[k],
                registered_members_ids=registered_members_dict,
            )
            university.id = ids[k]
            universities_list.append(university)
    return Universities(universities_list)


def restore_universities_properties_from_hdf5(
    world, file_path: str, chunk_size: int = 50000, domain_areas=None
):
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        universities = f["universities"]
        n_universities = universities.attrs["n_universities"]
        
        # Check if registered members data exists
        has_subgroup_data = "registered_members_subgroups" in universities
        subgroup_counts = {}
        subgroup_members = {}
        subgroup_cumulative_counts = {}
        
        if has_subgroup_data:
            # Get all subgroups
            subgroups = read_dataset(universities["registered_members_subgroups"], 0, universities["registered_members_subgroups"].shape[0])
            
            # For each subgroup, prepare the count and flattened arrays
            for subgroup_id in subgroups:
                sg_key = f"registered_members_count_sg{subgroup_id}"
                ids_key = f"registered_members_ids_sg{subgroup_id}"
                
                if sg_key in universities and ids_key in universities:
                    # Read counts for this subgroup
                    counts = read_dataset(universities[sg_key], 0, n_universities)
                    subgroup_counts[subgroup_id] = counts
                    
                    # Calculate cumulative counts for this subgroup
                    cumulative = np.concatenate(([0], np.cumsum(counts)))
                    subgroup_cumulative_counts[subgroup_id] = cumulative
                    
                    # Read flattened member IDs for this subgroup
                    if universities[ids_key].shape[0] > 0:
                        member_ids = read_dataset(universities[ids_key], 0, universities[ids_key].shape[0])
                        subgroup_members[subgroup_id] = member_ids
                    else:
                        subgroup_members[subgroup_id] = np.array([])
        
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
            
            # Restore registered_members_ids if available
            if has_subgroup_data and subgroups.size > 0:
                university_index = k
                registered_members_dict = {}
                
                # Process each subgroup
                for subgroup_id in subgroups:
                    if subgroup_id in subgroup_counts and subgroup_id in subgroup_members:
                        n_members = subgroup_counts[subgroup_id][university_index]
                        
                        if n_members > 0 and len(subgroup_members[subgroup_id]) > 0:
                            start_idx = subgroup_cumulative_counts[subgroup_id][university_index]
                            end_idx = subgroup_cumulative_counts[subgroup_id][university_index + 1]
                            
                            if start_idx < len(subgroup_members[subgroup_id]):
                                registered_members_dict[int(subgroup_id)] = subgroup_members[subgroup_id][start_idx:end_idx].tolist()
                
                # Always use dictionary format
                university.registered_members_ids = registered_members_dict
