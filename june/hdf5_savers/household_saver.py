import h5py
import numpy as np
import logging
from itertools import chain

from june.global_context import GlobalContext
from june.world import World
from june.groups import Household, Households, ExternalGroup
from june.groups.group.make_subgroups import SubgroupParams
from june.mpi_wrapper import mpi_rank
from .utils import read_dataset

nan_integer = -999

int_vlen_type = h5py.vlen_dtype(np.dtype("int64"))
str_vlen_type = h5py.vlen_dtype(np.dtype("S20"))
logger = logging.getLogger("household_saver")
if mpi_rank > 0:
    logger.propagate = False


def save_households_to_hdf5(
    households: Households, file_path: str, chunk_size: int = 50000
):
    """
    Saves the households object to hdf5 format file ``file_path``. Currently for each person,
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
    n_households = len(households)
    n_chunks = int(np.ceil(n_households / chunk_size))
    with h5py.File(file_path, "a") as f:
        households_dset = f.create_group("households")
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            ids = []
            areas = []
            super_areas = []
            types = []
            composition_types = []
            max_sizes = []
            registered_members_ids = []  # Add for storing registered_members_ids
            for household in households[idx1:idx2]:
                ids.append(household.id)
                if household.area is None:
                    areas.append(nan_integer)
                    super_areas.append(nan_integer)
                else:
                    areas.append(household.area.id)
                    super_areas.append(household.super_area.id)
                if household.type is None:
                    types.append(" ".encode("ascii", "ignore"))
                else:
                    types.append(household.type.encode("ascii", "ignore"))
                if household.composition_type is None:
                    composition_types.append(" ".encode("ascii", "ignore"))
                else:
                    composition_types.append(
                        household.composition_type.encode("ascii", "ignore")
                    )
                max_sizes.append(household.max_size)
                
                # Process registered_members_ids
                household_registered_members = {}
                if hasattr(household, 'registered_members_ids') and household.registered_members_ids is not None:
                    for subgroup_id, members in household.registered_members_ids.items():
                        household_registered_members[subgroup_id] = np.array(members, dtype=np.int64)
                registered_members_ids.append(household_registered_members)

            ids = np.array(ids, dtype=np.int64)
            areas = np.array(areas, dtype=np.int64)
            super_areas = np.array(super_areas, dtype=np.int64)
            types = np.array(types, dtype="S20")
            composition_types = np.array(composition_types, dtype="S20")
            max_sizes = np.array(max_sizes, dtype=np.float64)
            
            # Create datasets to store registered_members_ids
            # First, determine what subgroups exist across all households
            all_subgroups = set()
            for household_subgroups in registered_members_ids:
                all_subgroups.update(household_subgroups.keys())
            all_subgroups = sorted(list(all_subgroups))  # Ensure consistent ordering
            
            # Store subgroup IDs as integers
            subgroup_ids = np.array(all_subgroups, dtype=np.int64) if all_subgroups else np.array([], dtype=np.int64)
            
            # Create counts and flattened arrays for each subgroup
            subgroup_counts = {}
            flattened_subgroup_members = {}
            
            for subgroup_id in all_subgroups:
                # Count of members in this subgroup for each household
                counts = np.array([len(household_dict.get(subgroup_id, [])) for household_dict in registered_members_ids], dtype=np.int64)
                subgroup_counts[subgroup_id] = counts
                
                # Flatten all member IDs for this subgroup
                member_arrays = [household_dict.get(subgroup_id, np.array([], dtype=np.int64)) for household_dict in registered_members_ids]
                flattened = np.concatenate(member_arrays) if any(len(arr) > 0 for arr in member_arrays) else np.array([], dtype=np.int64)
                flattened_subgroup_members[subgroup_id] = flattened
            if chunk == 0:
                households_dset.attrs["n_households"] = n_households
                households_dset.create_dataset("id", data=ids, maxshape=(None,))
                households_dset.create_dataset("area", data=areas, maxshape=(None,))
                households_dset.create_dataset(
                    "super_area", data=super_areas, maxshape=(None,)
                )
                households_dset.create_dataset("type", data=types, maxshape=(None,))
                households_dset.create_dataset(
                    "composition_type", data=composition_types, maxshape=(None,)
                )
                households_dset.create_dataset(
                    "max_size", data=max_sizes, maxshape=(None,)
                )
                
                # Store registered_members_ids subgroups information
                if all_subgroups:  # Only create these datasets if we have subgroups
                    households_dset.create_dataset("registered_members_subgroups", data=subgroup_ids, maxshape=(None,))
                    
                    # Create datasets for each subgroup
                    for subgroup_id in all_subgroups:
                        # Store counts for this subgroup
                        households_dset.create_dataset(
                            f"registered_members_count_sg{subgroup_id}", 
                            data=subgroup_counts[subgroup_id], 
                            maxshape=(None,)
                        )
                        
                        # Store flattened members for this subgroup
                        flattened_members = flattened_subgroup_members[subgroup_id]
                        households_dset.create_dataset(
                            f"registered_members_ids_sg{subgroup_id}", 
                            data=flattened_members, 
                            maxshape=(None,)
                        )

            else:
                newshape = (households_dset["id"].shape[0] + ids.shape[0],)
                households_dset["id"].resize(newshape)
                households_dset["id"][idx1:idx2] = ids
                households_dset["area"].resize(newshape)
                households_dset["area"][idx1:idx2] = areas
                households_dset["super_area"].resize(newshape)
                households_dset["super_area"][idx1:idx2] = super_areas
                households_dset["type"].resize(newshape)
                households_dset["type"][idx1:idx2] = types
                households_dset["composition_type"].resize(newshape)
                households_dset["composition_type"][idx1:idx2] = composition_types
                households_dset["max_size"].resize(newshape)
                households_dset["max_size"][idx1:idx2] = max_sizes
                
                # Update registered members for subgroups
                if all_subgroups:  # Only update these datasets if we have subgroups
                    for subgroup_id in all_subgroups:
                        # Update counts for this subgroup
                        count_dataset = households_dset[f"registered_members_count_sg{subgroup_id}"]
                        count_dataset.resize(newshape)
                        count_dataset[idx1:idx2] = subgroup_counts[subgroup_id]
                        
                        # Update flattened IDs for this subgroup (variable length)
                        ids_dataset = households_dset[f"registered_members_ids_sg{subgroup_id}"]
                        flattened_members = flattened_subgroup_members[subgroup_id]
                        
                        if flattened_members.shape[0] > 0:
                            current_length = ids_dataset.shape[0]
                            new_length = current_length + flattened_members.shape[0]
                            ids_dataset.resize((new_length,))
                            ids_dataset[current_length:new_length] = flattened_members

        residences_to_visit_specs = []
        residences_to_visit_ids = []
        residences_to_visit_super_areas = []
        for household in households:
            if not household.residences_to_visit:
                residences_to_visit_specs.append(np.array(["none"], dtype="S20"))
                residences_to_visit_ids.append(np.array([nan_integer], dtype=np.int64))
                residences_to_visit_super_areas.append(
                    np.array([nan_integer], dtype=np.int64)
                )
            else:
                to_visit_ids = []
                to_visit_specs = []
                to_visit_super_areas = []
                for residence_type in household.residences_to_visit:
                    for residence_to_visit in household.residences_to_visit[
                        residence_type
                    ]:
                        to_visit_specs.append(residence_type)
                        to_visit_ids.append(residence_to_visit.id)
                        to_visit_super_areas.append(residence_to_visit.super_area.id)
                residences_to_visit_specs.append(np.array(to_visit_specs, dtype="S20"))
                residences_to_visit_ids.append(np.array(to_visit_ids, dtype=np.int64))
                residences_to_visit_super_areas.append(
                    np.array(to_visit_super_areas, dtype=np.int64)
                )

        if len(np.unique(list(chain(*residences_to_visit_ids)))) > 1:
            residences_to_visit_ids = np.array(
                residences_to_visit_ids, dtype=int_vlen_type
            )
            residences_to_visit_specs = np.array(
                residences_to_visit_specs, dtype=str_vlen_type
            )
            residences_to_visit_super_areas = np.array(
                residences_to_visit_super_areas, dtype=int_vlen_type
            )
        else:
            residences_to_visit_ids = np.array(residences_to_visit_ids, dtype=np.int64)
            residences_to_visit_specs = np.array(residences_to_visit_specs, dtype="S20")
            residences_to_visit_super_areas = np.array(
                residences_to_visit_super_areas, dtype=np.int64
            )
        households_dset.create_dataset(
            "residences_to_visit_ids", data=residences_to_visit_ids
        )
        households_dset.create_dataset(
            "residences_to_visit_specs", data=residences_to_visit_specs
        )
        households_dset.create_dataset(
            "residences_to_visit_super_areas", data=residences_to_visit_super_areas
        )


def load_households_from_hdf5(
    file_path: str, chunk_size=50000, domain_super_areas=None, config_filename=None
):
    """
    Loads households from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """

    Household_Class = Household
    disease_config = GlobalContext.get_disease_config()
    Household_Class.subgroup_params = SubgroupParams.from_disease_config(disease_config)

    logger.info("loading households...")
    households_list = []
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        households = f["households"]
        n_households = households.attrs["n_households"]
        n_chunks = int(np.ceil(n_households / chunk_size))
        
        # Check if registered members data exists
        has_subgroup_data = "registered_members_subgroups" in households
        subgroup_counts = {}
        subgroup_members = {}
        subgroup_cumulative_counts = {}
        
        if has_subgroup_data:
            # Get all subgroups
            subgroups = read_dataset(households["registered_members_subgroups"], 0, households["registered_members_subgroups"].shape[0])
            
            # For each subgroup, prepare the count and flattened arrays
            for subgroup_id in subgroups:
                sg_key = f"registered_members_count_sg{subgroup_id}"
                ids_key = f"registered_members_ids_sg{subgroup_id}"
                
                if sg_key in households and ids_key in households:
                    # Read counts for this subgroup
                    counts = read_dataset(households[sg_key], 0, n_households)
                    subgroup_counts[subgroup_id] = counts
                    
                    # Calculate cumulative counts for this subgroup
                    cumulative = np.concatenate(([0], np.cumsum(counts)))
                    subgroup_cumulative_counts[subgroup_id] = cumulative
                    
                    # Read flattened member IDs for this subgroup
                    if households[ids_key].shape[0] > 0:
                        member_ids = read_dataset(households[ids_key], 0, households[ids_key].shape[0])
                        subgroup_members[subgroup_id] = member_ids
                    else:
                        subgroup_members[subgroup_id] = np.array([])
        for chunk in range(n_chunks):
            logger.info(f"Loaded chunk {chunk} of {n_chunks}")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            length = idx2 - idx1
            ids = read_dataset(households["id"], idx1, idx2)
            types = read_dataset(households["type"], idx1, idx2)
            composition_types = read_dataset(households["composition_type"], idx1, idx2)
            max_sizes = read_dataset(households["max_size"], idx1, idx2)
            super_areas = read_dataset(households["super_area"], idx1, idx2)
            for k in range(length):
                if domain_super_areas is not None:
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                        
                # Get registered_members_ids for this household if available
                registered_members_dict = {}
                
                if has_subgroup_data and subgroups.size > 0:
                    household_index = idx1 + k
                    
                    # Get members for each subgroup
                    for subgroup_id in subgroups:
                        if subgroup_id in subgroup_counts and subgroup_id in subgroup_members:
                            n_members = subgroup_counts[subgroup_id][household_index]
                            
                            if n_members > 0 and len(subgroup_members[subgroup_id]) > 0:
                                start_idx = subgroup_cumulative_counts[subgroup_id][household_index]
                                end_idx = subgroup_cumulative_counts[subgroup_id][household_index + 1]
                                
                                if start_idx < len(subgroup_members[subgroup_id]):
                                    registered_members_dict[int(subgroup_id)] = subgroup_members[subgroup_id][start_idx:end_idx].tolist()
                
                household = Household_Class(
                    area=None,
                    type=types[k].decode(),
                    max_size=max_sizes[k],
                    composition_type=composition_types[k].decode(),
                    registered_members_ids=registered_members_dict,
                )
                households_list.append(household)
                household.id = ids[k]
    return Households(households_list)


def restore_households_properties_from_hdf5(
    world: World,
    file_path: str,
    chunk_size=50000,
    domain_super_areas=None,
    super_areas_to_domain_dict: dict = None,
):
    """
    Loads households from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    logger.info("restoring households...")
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        households = f["households"]
        n_households = households.attrs["n_households"]
        n_chunks = int(np.ceil(n_households / chunk_size))
        
        # Check if registered members data exists
        has_subgroup_data = "registered_members_subgroups" in households
        subgroup_counts = {}
        subgroup_members = {}
        subgroup_cumulative_counts = {}
        
        if has_subgroup_data:
            # Get all subgroups
            subgroups = read_dataset(households["registered_members_subgroups"], 0, households["registered_members_subgroups"].shape[0])
            
            # For each subgroup, prepare the count and flattened arrays
            for subgroup_id in subgroups:
                sg_key = f"registered_members_count_sg{subgroup_id}"
                ids_key = f"registered_members_ids_sg{subgroup_id}"
                
                if sg_key in households and ids_key in households:
                    # Read counts for this subgroup
                    counts = read_dataset(households[sg_key], 0, n_households)
                    subgroup_counts[subgroup_id] = counts
                    
                    # Calculate cumulative counts for this subgroup
                    cumulative = np.concatenate(([0], np.cumsum(counts)))
                    subgroup_cumulative_counts[subgroup_id] = cumulative
                    
                    # Read flattened member IDs for this subgroup
                    if households[ids_key].shape[0] > 0:
                        member_ids = read_dataset(households[ids_key], 0, households[ids_key].shape[0])
                        subgroup_members[subgroup_id] = member_ids
                    else:
                        subgroup_members[subgroup_id] = np.array([])
        for chunk in range(n_chunks):
            logger.info(f"Restored chunk {chunk} of {n_chunks}")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            length = idx2 - idx1
            ids = read_dataset(households["id"], idx1, idx2)
            super_areas = read_dataset(households["super_area"], idx1, idx2)
            areas = read_dataset(households["area"], idx1, idx2)
            residences_to_visit_ids = read_dataset(
                households["residences_to_visit_ids"], idx1, idx2
            )
            residences_to_visit_specs = read_dataset(
                households["residences_to_visit_specs"], idx1, idx2
            )
            residences_to_visit_super_areas = read_dataset(
                households["residences_to_visit_super_areas"], idx1, idx2
            )
            for k in range(length):
                if domain_super_areas is not None:
                    """
                    Note: if the relatives live outside the super area this will fail.
                    """
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                household = world.households.get_from_id(ids[k])
                area = world.areas.get_from_id(areas[k])
                household.area = area
                area.households.append(household)
                household.residents = tuple(household.people)
                
                # Restore registered_members_ids if available
                if has_subgroup_data and subgroups.size > 0:
                    household_index = idx1 + k
                    registered_members_dict = {}
                    
                    # Process each subgroup
                    for subgroup_id in subgroups:
                        if subgroup_id in subgroup_counts and subgroup_id in subgroup_members:
                            n_members = subgroup_counts[subgroup_id][household_index]
                            
                            if n_members > 0 and len(subgroup_members[subgroup_id]) > 0:
                                start_idx = subgroup_cumulative_counts[subgroup_id][household_index]
                                end_idx = subgroup_cumulative_counts[subgroup_id][household_index + 1]
                                
                                if start_idx < len(subgroup_members[subgroup_id]):
                                    registered_members_dict[int(subgroup_id)] = subgroup_members[subgroup_id][start_idx:end_idx].tolist()
                    
                    # Always use dictionary format
                    household.registered_members_ids = registered_members_dict
                # visits
                visit_ids = residences_to_visit_ids[k]
                if visit_ids[0] == nan_integer:
                    continue
                visit_specs = residences_to_visit_specs[k]
                visit_super_areas = residences_to_visit_super_areas[k]
                for visit_id, visit_spec, visit_super_area in zip(
                    visit_ids, visit_specs, visit_super_areas
                ):
                    if (
                        domain_super_areas is not None
                        and visit_super_area not in domain_super_areas
                    ):
                        residence = ExternalGroup(
                            id=visit_id,
                            domain_id=super_areas_to_domain_dict[visit_super_area],
                            spec=visit_spec.decode(),
                        )
                    else:
                        visit_spec = visit_spec.decode()
                        if visit_spec == "household":
                            residence = world.households.get_from_id(visit_id)
                        elif visit_spec == "care_home":
                            residence = world.care_homes.get_from_id(visit_id)
                    household.residences_to_visit[visit_spec] = (
                        *household.residences_to_visit[visit_spec],
                        residence,
                    )
