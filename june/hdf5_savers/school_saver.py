import h5py
import numpy as np

from june.global_context import GlobalContext
from june.groups import Schools, School
from june.world import World
from june.groups.group.make_subgroups import SubgroupParams
from .utils import read_dataset

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
            n_classrooms = []
            years = []
            areas = []
            super_areas = []
            registered_members_ids = []  # Add for storing registered_members_ids
            for school in schools[idx1:idx2]:
                ids.append(school.id)
                n_pupils_max.append(school.n_pupils_max)
                age_min.append(school.age_min)
                age_max.append(school.age_max)
                if type(school.sector) is float or school.sector is None:
                    sectors.append(" ".encode("ascii", "ignore"))
                else:
                    sectors.append(school.sector.encode("ascii", "ignore"))
                if school.area is None:
                    areas.append(nan_integer)
                    super_areas.append(nan_integer)
                else:
                    areas.append(school.area.id)
                    super_areas.append(school.super_area.id)
                coordinates.append(np.array(school.coordinates))
                n_classrooms.append(school.n_classrooms)
                years.append(np.array(school.years))
                
                # Process registered_members_ids
                school_registered_members = {}
                if hasattr(school, 'registered_members_ids') and school.registered_members_ids is not None:
                    for subgroup_id, members in school.registered_members_ids.items():
                        school_registered_members[subgroup_id] = np.array(members, dtype=np.int64)
                registered_members_ids.append(school_registered_members)

            ids = np.array(ids, dtype=np.int64)
            n_pupils_max = np.array(n_pupils_max, dtype=np.int64)
            age_min = np.array(age_min, dtype=np.int64)
            age_max = np.array(age_max, dtype=np.int64)
            sectors = np.array(sectors, dtype="S20")
            areas = np.array(areas, dtype=np.int64)
            super_areas = np.array(super_areas, dtype=np.int64)
            coordinates = np.array(coordinates, dtype=np.float64)
            n_classrooms = np.array(n_classrooms, dtype=np.int64)
            if len(years) < 2:
                years = np.array(years, dtype=np.int64)
            else:
                years = np.array(years, dtype=int_vlen_type)
                
            # Create datasets to store registered_members_ids
            # First, determine what subgroups exist across all schools
            all_subgroups = set()
            for school_subgroups in registered_members_ids:
                all_subgroups.update(school_subgroups.keys())
            all_subgroups = sorted(list(all_subgroups))  # Ensure consistent ordering
            
            # Store subgroup IDs as integers
            subgroup_ids = np.array(all_subgroups, dtype=np.int64)
            
            # Create counts and flattened arrays for each subgroup
            subgroup_counts = {}
            flattened_subgroup_members = {}
            
            for subgroup_id in all_subgroups:
                # Count of members in this subgroup for each school
                counts = np.array([len(school_dict.get(subgroup_id, [])) for school_dict in registered_members_ids], dtype=np.int64)
                subgroup_counts[subgroup_id] = counts
                
                # Flatten all member IDs for this subgroup
                member_arrays = [school_dict.get(subgroup_id, np.array([], dtype=np.int64)) for school_dict in registered_members_ids]
                flattened = np.concatenate(member_arrays) if any(len(arr) > 0 for arr in member_arrays) else np.array([], dtype=np.int64)
                flattened_subgroup_members[subgroup_id] = flattened
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
                schools_dset.create_dataset(
                    "super_area", data=super_areas, maxshape=(None,)
                )
                schools_dset.create_dataset(
                    "n_classrooms", data=n_classrooms, maxshape=(None,)
                )
                schools_dset.create_dataset("years", data=years)
                
                # Store registered_members_ids subgroups information
                if all_subgroups:  # Only create these datasets if we have subgroups
                    schools_dset.create_dataset("registered_members_subgroups", data=subgroup_ids, maxshape=(None,))
                    
                    # Create datasets for each subgroup
                    for subgroup_id in all_subgroups:
                        # Store counts for this subgroup
                        schools_dset.create_dataset(
                            f"registered_members_count_sg{subgroup_id}", 
                            data=subgroup_counts[subgroup_id], 
                            maxshape=(None,)
                        )
                        
                        # Store flattened members for this subgroup
                        flattened_members = flattened_subgroup_members[subgroup_id]
                        schools_dset.create_dataset(
                            f"registered_members_ids_sg{subgroup_id}", 
                            data=flattened_members, 
                            maxshape=(None,)
                        )
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
                schools_dset["super_area"].resize(newshape[0], axis=0)
                schools_dset["super_area"][idx1:idx2] = super_areas
                schools_dset["n_classrooms"].resize(newshape[0], axis=0)
                schools_dset["n_classrooms"][idx1:idx2] = n_classrooms
                schools_dset["years"].resize(newshape[0], axis=0)
                schools_dset["years"][idx1:idx2] = years
                
                # Update registered members for subgroups
                if all_subgroups:  # Only update these datasets if we have subgroups
                    for subgroup_id in all_subgroups:
                        # Update counts for this subgroup
                        count_dataset = schools_dset[f"registered_members_count_sg{subgroup_id}"]
                        count_dataset.resize(newshape)
                        count_dataset[idx1:idx2] = subgroup_counts[subgroup_id]
                        
                        # Update flattened IDs for this subgroup (variable length)
                        ids_dataset = schools_dset[f"registered_members_ids_sg{subgroup_id}"]
                        flattened_members = flattened_subgroup_members[subgroup_id]
                        
                        if flattened_members.shape[0] > 0:
                            current_length = ids_dataset.shape[0]
                            new_length = current_length + flattened_members.shape[0]
                            ids_dataset.resize((new_length,))
                            ids_dataset[current_length:new_length] = flattened_members


def load_schools_from_hdf5(
    file_path: str,
    chunk_size: int = 50000,
    domain_super_areas=None,
    config_filename=None,
):
    """
    Loads schools from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """

    School_Class = School
    disease_config = GlobalContext.get_disease_config()
    School_Class.subgroup_params = SubgroupParams.from_disease_config(disease_config)

    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        schools = f["schools"]
        schools_list = []
        n_schools = schools.attrs["n_schools"]
        n_chunks = int(np.ceil(n_schools / chunk_size))
        
        # Check if registered members data exists
        has_subgroup_data = "registered_members_subgroups" in schools
        subgroup_counts = {}
        subgroup_members = {}
        subgroup_cumulative_counts = {}
        
        if has_subgroup_data:
            # Get all subgroups
            subgroups = read_dataset(schools["registered_members_subgroups"], 0, schools["registered_members_subgroups"].shape[0])
            
            # For each subgroup, prepare the count and flattened arrays
            for subgroup_id in subgroups:
                sg_key = f"registered_members_count_sg{subgroup_id}"
                ids_key = f"registered_members_ids_sg{subgroup_id}"
                
                if sg_key in schools and ids_key in schools:
                    # Read counts for this subgroup
                    counts = read_dataset(schools[sg_key], 0, n_schools)
                    subgroup_counts[subgroup_id] = counts
                    
                    # Calculate cumulative counts for this subgroup
                    cumulative = np.concatenate(([0], np.cumsum(counts)))
                    subgroup_cumulative_counts[subgroup_id] = cumulative
                    
                    # Read flattened member IDs for this subgroup
                    if schools[ids_key].shape[0] > 0:
                        member_ids = read_dataset(schools[ids_key], 0, schools[ids_key].shape[0])
                        subgroup_members[subgroup_id] = member_ids
                    else:
                        subgroup_members[subgroup_id] = np.array([])
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_schools)
            ids = read_dataset(schools["id"], idx1, idx2)
            n_pupils_max = read_dataset(schools["n_pupils_max"], idx1, idx2)
            age_min = read_dataset(schools["age_min"], idx1, idx2)
            age_max = read_dataset(schools["age_max"], idx1, idx2)
            coordinates = read_dataset(schools["coordinates"], idx1, idx2)
            n_classrooms = read_dataset(schools["n_classrooms"], idx1, idx2)
            years = read_dataset(schools["years"], idx1, idx2)
            super_areas = read_dataset(schools["super_area"], idx1, idx2)
            sectors = read_dataset(schools["sector"], idx1, idx2)
            for k in range(idx2 - idx1):
                if domain_super_areas is not None:
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                sector = sectors[k]
                if sector.decode() == " ":
                    sector = None
                else:
                    sector = sector.decode()
                # Get registered_members_ids for this school if available
                registered_members_dict = {}
                
                if has_subgroup_data and subgroups.size > 0:
                    school_index = idx1 + k
                    
                    # Get members for each subgroup
                    for subgroup_id in subgroups:
                        if subgroup_id in subgroup_counts and subgroup_id in subgroup_members:
                            n_members = subgroup_counts[subgroup_id][school_index]
                            
                            if n_members > 0 and len(subgroup_members[subgroup_id]) > 0:
                                start_idx = subgroup_cumulative_counts[subgroup_id][school_index]
                                end_idx = subgroup_cumulative_counts[subgroup_id][school_index + 1]
                                
                                if start_idx < len(subgroup_members[subgroup_id]):
                                    registered_members_dict[int(subgroup_id)] = subgroup_members[subgroup_id][start_idx:end_idx].tolist()
                
                school = School_Class(
                    coordinates=coordinates[k],
                    n_pupils_max=n_pupils_max[k],
                    age_min=age_min[k],
                    age_max=age_max[k],
                    sector=sector,
                    n_classrooms=n_classrooms[k],
                    years=years[k],
                    registered_members_ids=registered_members_dict,
                )
                school.id = ids[k]
                schools_list.append(school)
    return Schools(schools_list)


def restore_school_properties_from_hdf5(
    world: World, file_path: str, chunk_size, domain_super_areas=None
):
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        schools = f["schools"]
        n_schools = schools.attrs["n_schools"]
        n_chunks = int(np.ceil(n_schools / chunk_size))
        
        # Check if registered members data exists
        has_subgroup_data = "registered_members_subgroups" in schools
        subgroup_counts = {}
        subgroup_members = {}
        subgroup_cumulative_counts = {}
        
        if has_subgroup_data:
            # Get all subgroups
            subgroups = read_dataset(schools["registered_members_subgroups"], 0, schools["registered_members_subgroups"].shape[0])
            
            # For each subgroup, prepare the count and flattened arrays
            for subgroup_id in subgroups:
                sg_key = f"registered_members_count_sg{subgroup_id}"
                ids_key = f"registered_members_ids_sg{subgroup_id}"
                
                if sg_key in schools and ids_key in schools:
                    # Read counts for this subgroup
                    counts = read_dataset(schools[sg_key], 0, n_schools)
                    subgroup_counts[subgroup_id] = counts
                    
                    # Calculate cumulative counts for this subgroup
                    cumulative = np.concatenate(([0], np.cumsum(counts)))
                    subgroup_cumulative_counts[subgroup_id] = cumulative
                    
                    # Read flattened member IDs for this subgroup
                    if schools[ids_key].shape[0] > 0:
                        member_ids = read_dataset(schools[ids_key], 0, schools[ids_key].shape[0])
                        subgroup_members[subgroup_id] = member_ids
                    else:
                        subgroup_members[subgroup_id] = np.array([])
        
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_schools)
            length = idx2 - idx1
            ids = read_dataset(schools["id"], idx1, idx2)
            areas = read_dataset(schools["area"], idx1, idx2)
            super_areas = read_dataset(schools["super_area"], idx1, idx2)
            for k in range(length):
                if domain_super_areas is not None:
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                        
                school = world.schools.get_from_id(ids[k])
                
                area = areas[k]
                if area == nan_integer:
                    school.area = None
                else:
                    school.area = world.areas.get_from_id(area)
                    
                # Restore registered_members_ids if available
                if has_subgroup_data and subgroups.size > 0:
                    school_index = idx1 + k
                    registered_members_dict = {}
                    
                    # Process each subgroup
                    for subgroup_id in subgroups:
                        if subgroup_id in subgroup_counts and subgroup_id in subgroup_members:
                            n_members = subgroup_counts[subgroup_id][school_index]
                            
                            if n_members > 0 and len(subgroup_members[subgroup_id]) > 0:
                                start_idx = subgroup_cumulative_counts[subgroup_id][school_index]
                                end_idx = subgroup_cumulative_counts[subgroup_id][school_index + 1]
                                
                                if start_idx < len(subgroup_members[subgroup_id]):
                                    registered_members_dict[int(subgroup_id)] = subgroup_members[subgroup_id][start_idx:end_idx].tolist()
                    
                    # Always use dictionary format
                    school.registered_members_ids = registered_members_dict
