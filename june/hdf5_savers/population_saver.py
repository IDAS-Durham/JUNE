import h5py
import numpy as np
import logging


from .utils import read_dataset
from june.groups import ExternalSubgroup, ExternalGroup
from june.groups.travel import ModeOfTransport
from june.demography import Population, Person
from june.demography.person import Activities
from june.geography import ExternalSuperArea
from june.world import World
from june.mpi_wrapper import mpi_rank

logger = logging.getLogger("population saver")
if mpi_rank > 0:
    logger.propagate = False

nan_integer = -999  # only used to store/load hdf5 integer arrays with inf/nan values
spec_mapper = {
    "hospital": "hospitals",
    "company": "companies",
    "school": "schools",
    "household": "households",
    "care_home": "care_homes",
    "university": "universities",
    "pub": "pubs",
    "grocery": "groceries",
    "cinema": "cinemas",
}

def save_population_to_hdf5(population: Population, file_path: str, chunk_size: int = 100000):
    """
    Saves the Population object to hdf5 format file ``file_path``. Includes saving friends as flattened [friend_id, home_rank] arrays.
    """
    n_people = len(population.people)
    n_chunks = int(np.ceil(n_people / chunk_size))
    
    with h5py.File(file_path, "a") as f:
        people_dset = f.create_group("population")
        vltype = h5py.vlen_dtype(np.int64)  # For variable-length arrays like friend lists
        vlstr_dtype = h5py.vlen_dtype(np.dtype("S50"))

        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_people)

            ids = []
            ages = []
            sexes = []
            ethns = []
            areas = []
            super_areas = []
            work_super_areas = []
            work_super_areas_cities = []
            work_super_area_coords = []
            sectors = []
            sub_sectors = []
            group_ids = []
            group_specs = []
            group_super_areas = []
            subgroup_types = []
            mode_of_transport_description = []
            mode_of_transport_is_public = []
            lockdown_status = []
            friends_list = []  # For storing friend IDs
            hobbies_list = []  # For storing hobbies
            
            """ # Sexual relationship data
            relationship_status_type = []
            relationship_status_cheating = []
            sexual_orientation_type = []
            sexual_risk_profile_level = []
            sexual_risk_profile_protection = []
            sexual_risk_profile_testing = []
            exclusive_partners_list = []
            non_exclusive_partners_list = [] """

            for person in population.people[idx1:idx2]:
                ids.append(person.id)
                ages.append(person.age)
                sexes.append(person.sex.encode("ascii", "ignore"))
                
                ethns.append(person.ethnicity.encode("ascii", "ignore") if person.ethnicity else " ".encode("ascii", "ignore"))
                areas.append(person.area.id if person.area else nan_integer)
                super_areas.append(person.area.super_area.id if person.area and person.area.super_area else nan_integer)
                
                if person.work_super_area:
                    work_super_areas.append(person.work_super_area.id)
                    work_super_area_coords.append(np.array(person.work_super_area.coordinates, dtype=np.float64))
                    work_super_areas_cities.append(person.work_super_area.city.id if person.work_super_area.city else nan_integer)
                else:
                    work_super_areas.append(nan_integer)
                    work_super_area_coords.append(np.array([nan_integer, nan_integer], dtype=np.float64))
                    work_super_areas_cities.append(nan_integer)
                
                sectors.append(person.sector.encode("ascii", "ignore") if person.sector else " ".encode("ascii", "ignore"))
                sub_sectors.append(person.sub_sector.encode("ascii", "ignore") if person.sub_sector else " ".encode("ascii", "ignore"))
                lockdown_status.append(person.lockdown_status.encode("ascii", "ignore") if person.lockdown_status else " ".encode("ascii", "ignore"))

                gids = []
                stypes = []
                specs = []
                group_super_areas_temp = []

                for subgroup in person.subgroups.iter():
                    if subgroup is None:
                        gids.append(nan_integer)
                        stypes.append(nan_integer)
                        specs.append(" ".encode("ascii", "ignore"))
                        group_super_areas_temp.append(nan_integer)
                    else:
                        gids.append(subgroup.group.id)
                        stypes.append(subgroup.subgroup_type)
                        specs.append(subgroup.group.spec.encode("ascii", "ignore"))
                        group_super_areas_temp.append(subgroup.group.super_area.id if subgroup.group.super_area else nan_integer)
                
                group_specs.append(np.array(specs, dtype="S20"))
                group_ids.append(np.array(gids, dtype=np.int64))
                subgroup_types.append(np.array(stypes, dtype=np.int64))
                group_super_areas.append(np.array(group_super_areas_temp, dtype=np.int64))

                mode_of_transport_description.append(
                    person.mode_of_transport.description.encode("ascii", "ignore") if person.mode_of_transport else " ".encode("ascii", "ignore")
                )
                mode_of_transport_is_public.append(person.mode_of_transport.is_public if person.mode_of_transport else False)

                # Save friends with hobbies as structured data
                if person.friends:
                    friend_data_list = []
                    for friend_id, friend_data in person.friends.items():
                        # Handle both old format (just home_rank) and new format (dict)
                        if isinstance(friend_data, dict):
                            home_rank = friend_data.get("home_rank", 0)
                            hobbies = friend_data.get("hobbies", [])
                        else:
                            # Old format - just home_rank
                            home_rank = friend_data
                            hobbies = []
                        
                        # Store as [friend_id, home_rank, num_hobbies, hobby1, hobby2, ...]
                        friend_entry = [friend_id, home_rank, len(hobbies)]
                        friend_entry.extend([h.encode("ascii", "ignore") for h in hobbies])
                        friend_data_list.extend(friend_entry)
                    
                    friends_list.append(friend_data_list)
                else:
                    friends_list.append([])
                
                # Save hobbies as list of byte strings
                hobbies_as_bytes = [h.encode("ascii", "ignore") for h in person.hobbies]
                hobbies_list.append(hobbies_as_bytes)
                
                """ # Save sexual relationship data
                # 1. Relationship status
                if hasattr(person, "relationship_status") and isinstance(person.relationship_status, dict):
                    rel_type = person.relationship_status.get("type", "single")
                    rel_cheating = person.relationship_status.get("cheating", False)
                    relationship_status_type.append(rel_type.encode("ascii", "ignore"))
                    relationship_status_cheating.append(rel_cheating)
                else:
                    relationship_status_type.append("single".encode("ascii", "ignore"))
                    relationship_status_cheating.append(False)
                
                # 2. Sexual orientation
                if hasattr(person, "sexual_orientation") and isinstance(person.sexual_orientation, dict):
                    orient_type = person.sexual_orientation.get("orientation", "heterosexual")
                    sexual_orientation_type.append(orient_type.encode("ascii", "ignore"))
                else:
                    sexual_orientation_type.append("heterosexual".encode("ascii", "ignore"))
                
                # 3. Sexual risk profile
                if hasattr(person, "sexual_risk_profile") and isinstance(person.sexual_risk_profile, dict):
                    risk_level = person.sexual_risk_profile.get("level", "low")
                    protection = person.sexual_risk_profile.get("protection_usage", 0.8)
                    testing = person.sexual_risk_profile.get("testing_frequency", 180)
                    sexual_risk_profile_level.append(risk_level.encode("ascii", "ignore"))
                    sexual_risk_profile_protection.append(protection)
                    sexual_risk_profile_testing.append(testing)
                else:
                    sexual_risk_profile_level.append("low".encode("ascii", "ignore"))
                    sexual_risk_profile_protection.append(0.8)
                    sexual_risk_profile_testing.append(180)
                
                # 4. Sexual partners - store exclusive and non_exclusive partners
                if hasattr(person, "sexual_partners") and isinstance(person.sexual_partners, dict):
                    exclusive_partners = list(person.sexual_partners.get("exclusive", set()))
                    non_exclusive_partners = list(person.sexual_partners.get("non_exclusive", set()))
                    exclusive_partners_list.append(exclusive_partners)
                    non_exclusive_partners_list.append(non_exclusive_partners)
                else:
                    exclusive_partners_list.append([])
                    non_exclusive_partners_list.append([]) """
            
            # Convert friends lists to structured arrays for HDF5 storage
            friends_data = []
            for friend_data_list in friends_list:
                if friend_data_list:  # If person has friends
                    # friend_data_list is already a flat list: [friend_id1, home_rank1, num_hobbies1, hobby1, hobby2, ...]
                    # We need to store this as mixed types, so convert strings to bytes and combine
                    mixed_data = []
                    i = 0
                    while i < len(friend_data_list):
                        # friend_id (int)
                        mixed_data.append(friend_data_list[i])
                        i += 1
                        # home_rank (int)  
                        mixed_data.append(friend_data_list[i])
                        i += 1
                        # num_hobbies (int)
                        num_hobbies = friend_data_list[i]
                        mixed_data.append(num_hobbies)
                        i += 1
                        # hobbies (bytes)
                        for _ in range(num_hobbies):
                            if i < len(friend_data_list):
                                hobby_bytes = friend_data_list[i]
                                # Convert to int representation of bytes for storage
                                if isinstance(hobby_bytes, bytes):
                                    # Store length followed by bytes as integers
                                    mixed_data.append(len(hobby_bytes))
                                    mixed_data.extend([int(b) for b in hobby_bytes])
                                else:
                                    # Fallback for string
                                    hobby_str = str(hobby_bytes)
                                    hobby_bytes = hobby_str.encode("ascii", "ignore")
                                    mixed_data.append(len(hobby_bytes))
                                    mixed_data.extend([int(b) for b in hobby_bytes])
                                i += 1
                    
                    friends_data.append(np.array(mixed_data, dtype=np.int64))
                else:  # If person has no friends
                    friends_data.append(np.array([], dtype=np.int64))
                
            # Convert hobbies lists to simple list of arrays
            hobbies_data = []
            for hoblist in hobbies_list:
                hobbies_data.append(np.array(hoblist, dtype="S50"))
                
            """ # Convert partner lists to flat numpy arrays first with special handling for empty arrays
            exclusive_partners_data = []
            for partners in exclusive_partners_list:
                # Ensure proper creation of arrays even when empty
                if not partners:  # For empty lists
                    exclusive_partners_data.append(np.array([], dtype=np.int64))
                else:
                    exclusive_partners_data.append(np.array(partners, dtype=np.int64))
                
            non_exclusive_partners_data = []
            for partners in non_exclusive_partners_list:
                # Ensure proper creation of arrays even when empty
                if not partners:  # For empty lists
                    non_exclusive_partners_data.append(np.array([], dtype=np.int64))
                else:
                    non_exclusive_partners_data.append(np.array(partners, dtype=np.int64)) """
                
            # Note: casual_partners_list is no longer used in the updated relationship model

            if chunk == 0:
                people_dset.attrs["n_people"] = n_people
                people_dset.create_dataset("id", data=np.array(ids, dtype=np.int64), maxshape=(None,), chunks=True)
                people_dset.create_dataset("age", data=np.array(ages, dtype=np.int64), maxshape=(None,), chunks=True)
                people_dset.create_dataset("sex", data=np.array(sexes, dtype="S10"), maxshape=(None,), chunks=True)
                people_dset.create_dataset("sector", data=np.array(sectors, dtype="S30"), maxshape=(None,), chunks=True)
                people_dset.create_dataset("sub_sector", data=np.array(sub_sectors, dtype="S30"), maxshape=(None,), chunks=True)
                people_dset.create_dataset("ethnicity", data=np.array(ethns, dtype="S10"), maxshape=(None,), chunks=True)
                people_dset.create_dataset("area", data=np.array(areas, dtype=np.int64), maxshape=(None,), chunks=True)
                people_dset.create_dataset("super_area", data=np.array(super_areas, dtype=np.int64), maxshape=(None,), chunks=True)
                people_dset.create_dataset("work_super_area", data=np.array(work_super_areas, dtype=np.int64), maxshape=(None,), chunks=True)
                people_dset.create_dataset("work_super_area_coords", data=np.array(work_super_area_coords, dtype=np.float64), maxshape=(None, 2), chunks=True)
                people_dset.create_dataset("work_super_area_city", data=np.array(work_super_areas_cities, dtype=np.int64), maxshape=(None,), chunks=True)
                people_dset.create_dataset("group_ids", data=np.array(group_ids, dtype=np.int64), maxshape=(None, len(group_ids[0])), chunks=True)
                people_dset.create_dataset("group_specs", data=np.array(group_specs, dtype="S20"), maxshape=(None, len(group_specs[0])), chunks=True)
                people_dset.create_dataset("subgroup_types", data=np.array(subgroup_types, dtype=np.int64), maxshape=(None, len(subgroup_types[0])), chunks=True)
                people_dset.create_dataset("group_super_areas", data=np.array(group_super_areas, dtype=np.int64), maxshape=(None, len(group_super_areas[0])), chunks=True)
                people_dset.create_dataset("mode_of_transport_description", data=np.array(mode_of_transport_description, dtype="S100"), maxshape=(None,), chunks=True)
                people_dset.create_dataset("mode_of_transport_is_public", data=np.array(mode_of_transport_is_public, dtype=bool), maxshape=(None,), chunks=True)
                people_dset.create_dataset("lockdown_status", data=np.array(lockdown_status, dtype="S20"), maxshape=(None,), chunks=True)
                
                # Create friends dataset - simplified approach
                try:
                    people_dset.create_dataset(
                        "friends",
                        data=friends_data,
                        dtype=h5py.vlen_dtype(np.dtype('int64')),
                        chunks=True,
                        maxshape=(None,)
                    )
                except Exception as e:
                    logger.error(f"Error creating friends dataset: {e}")
                
                # Create hobbies dataset - simplified approach
                try:
                    people_dset.create_dataset(
                        "hobbies",
                        data=hobbies_data,
                        dtype=h5py.vlen_dtype(np.dtype('S50')),
                        chunks=True,
                        maxshape=(None,)
                    )
                except Exception as e:
                    logger.error(f"Error creating hobbies dataset: {e}")
                
                """ # Create sexual relationship datasets
                # Relationship status
                people_dset.create_dataset(
                    "relationship_status_type",
                    data=np.array(relationship_status_type, dtype="S20"),
                    maxshape=(None,),
                    chunks=True
                )
                people_dset.create_dataset(
                    "relationship_status_cheating",
                    data=np.array(relationship_status_cheating, dtype=bool),
                    maxshape=(None,),
                    chunks=True
                )
                
                # Sexual orientation
                people_dset.create_dataset(
                    "sexual_orientation_type",
                    data=np.array(sexual_orientation_type, dtype="S20"),
                    maxshape=(None,),
                    chunks=True
                )
                
                
                # Sexual risk profile
                people_dset.create_dataset(
                    "sexual_risk_profile_level",
                    data=np.array(sexual_risk_profile_level, dtype="S10"),
                    maxshape=(None,),
                    chunks=True
                )
                people_dset.create_dataset(
                    "sexual_risk_profile_protection",
                    data=np.array(sexual_risk_profile_protection, dtype=np.float64),
                    maxshape=(None,),
                    chunks=True
                )
                people_dset.create_dataset(
                    "sexual_risk_profile_testing",
                    data=np.array(sexual_risk_profile_testing, dtype=np.int64),
                    maxshape=(None,),
                    chunks=True
                )
                
                # Sexual partners
                # Create exclusive partners dataset with the new terminology
                try:
                    logger.info("Creating exclusive_partners dataset...")
                    # Add extra data validation and special handling for variable-length datasets
                    # Debugging information about the partner data before dataset creation
                    logger.info(f"exclusive_partners_data length before creation: {len(exclusive_partners_data)}")
                    if len(exclusive_partners_data) > 0:
                        logger.info(f"First array shape: {exclusive_partners_data[0].shape}, dtype: {exclusive_partners_data[0].dtype}")
                        
                    # Ensure proper creation of HDF5 dataset with special handling for empty arrays
                    people_dset.create_dataset(
                        "exclusive_partners",
                        data=exclusive_partners_data,
                        dtype=h5py.vlen_dtype(np.dtype('int64')),
                        chunks=True,
                        maxshape=(None,)
                    )
                    logger.info("Exclusive partners dataset created successfully")
                except Exception as e:
                    logger.error(f"Error creating exclusive partners dataset: {e}")
                    
                # Create non-exclusive partners dataset with the new terminology
                try:
                    logger.info("Creating non_exclusive_partners dataset...")
                    # Add extra data validation and special handling for variable-length datasets
                    # Debugging information about the partner data before dataset creation
                    logger.info(f"non_exclusive_partners_data length before creation: {len(non_exclusive_partners_data)}")
                    if len(non_exclusive_partners_data) > 0:
                        logger.info(f"First array shape: {non_exclusive_partners_data[0].shape}, dtype: {non_exclusive_partners_data[0].dtype}")
                        
                    # Ensure proper creation of HDF5 dataset with special handling for empty arrays
                    people_dset.create_dataset(
                        "non_exclusive_partners",
                        data=non_exclusive_partners_data,
                        dtype=h5py.vlen_dtype(np.dtype('int64')),
                        chunks=True,
                        maxshape=(None,)
                    )
                    logger.info("Non-exclusive partners dataset created successfully")
                except Exception as e:
                    logger.error(f"Error creating non-exclusive partners dataset: {e}")
                 """
                # Note: We're no longer using casual_partners in the new relationship model

            else:
                current_len = people_dset["id"].shape[0]
                new_len = current_len + len(ids)

                # Update all datasets
                ds = people_dset["id"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(ids, dtype=np.int64)

                ds = people_dset["age"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(ages, dtype=np.int64)

                ds = people_dset["sex"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(sexes, dtype="S10")

                ds = people_dset["sector"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(sectors, dtype="S30")

                ds = people_dset["sub_sector"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(sub_sectors, dtype="S30")

                ds = people_dset["ethnicity"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(ethns, dtype="S10")

                ds = people_dset["area"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(areas, dtype=np.int64)

                ds = people_dset["super_area"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(super_areas, dtype=np.int64)

                ds = people_dset["work_super_area"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(work_super_areas, dtype=np.int64)

                ds = people_dset["work_super_area_coords"]
                ds.resize((new_len, 2))
                ds[current_len:new_len, :] = np.array(work_super_area_coords, dtype=np.float64)

                ds = people_dset["work_super_area_city"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(work_super_areas_cities, dtype=np.int64)

                ds = people_dset["group_ids"]
                ds.resize((new_len, group_ids[0].size))
                ds[current_len:new_len, :] = np.array(group_ids, dtype=np.int64)

                ds = people_dset["group_specs"]
                ds.resize((new_len, group_specs[0].size))
                ds[current_len:new_len, :] = np.array(group_specs, dtype="S20")

                ds = people_dset["subgroup_types"]
                ds.resize((new_len, subgroup_types[0].size))
                ds[current_len:new_len, :] = np.array(subgroup_types, dtype=np.int64)

                ds = people_dset["group_super_areas"]
                ds.resize((new_len, group_super_areas[0].size))
                ds[current_len:new_len, :] = np.array(group_super_areas, dtype=np.int64)

                ds = people_dset["mode_of_transport_description"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(mode_of_transport_description, dtype="S100")

                ds = people_dset["mode_of_transport_is_public"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(mode_of_transport_is_public, dtype=bool)

                ds = people_dset["lockdown_status"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(lockdown_status, dtype="S20")

                # Update friends dataset with better error handling
                try:
                    friends_dataset = people_dset["friends"]
                    friends_dataset.resize((new_len,))
                    for i, friends in enumerate(friends_data):
                        friends_dataset[current_len + i] = friends
                except Exception as e:
                    logger.error(f"Error updating friends dataset: {e}")
                
                # Update hobbies dataset with better error handling
                try:
                    hobbies_dataset = people_dset["hobbies"]
                    hobbies_dataset.resize((new_len,))
                    for i, hob_array in enumerate(hobbies_data):
                        hobbies_dataset[current_len + i] = hob_array
                except Exception as e:
                    logger.error(f"Error updating hobbies dataset: {e}")
                    
                """ # Update sexual relationship datasets
                # Relationship status
                ds = people_dset["relationship_status_type"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(relationship_status_type, dtype="S20")
                
                ds = people_dset["relationship_status_cheating"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(relationship_status_cheating, dtype=bool)
                
                # Sexual orientation
                ds = people_dset["sexual_orientation_type"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(sexual_orientation_type, dtype="S20")
                
                # Sexual risk profile
                ds = people_dset["sexual_risk_profile_level"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(sexual_risk_profile_level, dtype="S10")
                
                ds = people_dset["sexual_risk_profile_protection"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(sexual_risk_profile_protection, dtype=np.float64)
                
                ds = people_dset["sexual_risk_profile_testing"]
                ds.resize((new_len,))
                ds[current_len:new_len] = np.array(sexual_risk_profile_testing, dtype=np.int64)
                
                # Update sexual partners datasets with better error handling
                try:
                    exclusive_partners_dataset = people_dset["exclusive_partners"]
                    exclusive_partners_dataset.resize((new_len,))
                    for i, partners in enumerate(exclusive_partners_data):
                        exclusive_partners_dataset[current_len + i] = partners
                    logger.info("Updated exclusive partners dataset successfully")
                except Exception as e:
                    logger.error(f"Error updating exclusive partners dataset: {e}")
                    
                try:
                    non_exclusive_partners_dataset = people_dset["non_exclusive_partners"]
                    non_exclusive_partners_dataset.resize((new_len,))
                    for i, partners in enumerate(non_exclusive_partners_data):
                        non_exclusive_partners_dataset[current_len + i] = partners
                    logger.info("Updated non-exclusive partners dataset successfully")
                except Exception as e:
                    logger.error(f"Error updating non-exclusive partners dataset: {e}") """

    logger.info("Population saved successfully.")

def load_population_from_hdf5(file_path: str, chunk_size=100000, domain_super_areas=None):
    """
    Loads the population from an HDF5 file located at ``file_path``.
    The `friends` attribute is read as flattened [friend_id, home_rank] arrays and converted
    back to a dictionary {friend_id: home_rank} on each person.
    """
    people = []
    logger.info("loading population...")

    # Clear the Person class's friend location registry before loading


    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        population = f["population"]

        # read in chunks of 100k people
        n_people = population.attrs["n_people"]
        n_chunks = int(np.ceil(n_people / chunk_size))

        for chunk in range(n_chunks):
            logger.info(f"Loaded chunk {chunk+1} of {n_chunks}")

            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_people)

            # -- Read the basic attributes (IDs, ages, sexes, etc.) --
            ids = read_dataset(population["id"], idx1, idx2)
            ages = read_dataset(population["age"], idx1, idx2)
            sexes = read_dataset(population["sex"], idx1, idx2)
            ethns = read_dataset(population["ethnicity"], idx1, idx2)
            super_areas = read_dataset(population["super_area"], idx1, idx2)
            
            sectors = read_dataset(population["sector"], idx1, idx2)
            sub_sectors = read_dataset(population["sub_sector"], idx1, idx2)
            lockdown_status = read_dataset(population["lockdown_status"], idx1, idx2)

            mode_of_transport_is_public_list = read_dataset(
                population["mode_of_transport_is_public"], idx1, idx2
            )
            mode_of_transport_description_list = read_dataset(
                population["mode_of_transport_description"], idx1, idx2
            )

            # Modified friends handling
            friends_data = population["friends"][idx1:idx2]  # Load friend IDs

            # (NEW) Read the hobbies data (variable-length array of byte strings)
            # shape = (n_people,). Each element is an array of b"somehobby"
            hobbies_data = population["hobbies"][idx1:idx2]
            
            """ # Read sexual relationship data
            # Relationship status
            relationship_status_type_data = read_dataset(population["relationship_status_type"], idx1, idx2)
            relationship_status_cheating_data = read_dataset(population["relationship_status_cheating"], idx1, idx2)
            
            # Sexual orientation
            sexual_orientation_type_data = read_dataset(population["sexual_orientation_type"], idx1, idx2)
            
            # Sexual risk profile
            sexual_risk_profile_level_data = read_dataset(population["sexual_risk_profile_level"], idx1, idx2)
            sexual_risk_profile_protection_data = read_dataset(population["sexual_risk_profile_protection"], idx1, idx2)
            sexual_risk_profile_testing_data = read_dataset(population["sexual_risk_profile_testing"], idx1, idx2)
            
            
            exclusive_partners_data = population["exclusive_partners"][idx1:idx2]
            
                
            non_exclusive_partners_data = population["non_exclusive_partners"][idx1:idx2] """
            
            for k in range(idx2 - idx1):
                if domain_super_areas is not None:
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError("if `domain_super_areas` is specified, I expect not-None super areas.")
                    if super_area not in domain_super_areas:
                        continue

                # Convert " " to None for ethnicity if needed
                raw_ethn = ethns[k].decode()
                ethn = None if raw_ethn == " " else raw_ethn

                # Build the Person
                person = Person.from_attributes(
                    id=ids[k],
                    age=ages[k],
                    sex=sexes[k].decode(),
                    ethnicity=ethn
                )
                # Initialize friend relationships as dictionary {friend_id: {"home_rank": rank, "hobbies": [...]}}
                friend_data = friends_data[k]  # Mixed data array
                if len(friend_data) > 0:
                    # Parse the mixed data structure
                    person.friends = {}
                    i = 0
                    while i < len(friend_data):
                        if i + 2 >= len(friend_data):
                            break
                        
                        friend_id = int(friend_data[i])
                        home_rank = int(friend_data[i + 1])
                        num_hobbies = int(friend_data[i + 2])
                        i += 3
                        
                        # Read hobbies
                        hobbies = []
                        for _ in range(num_hobbies):
                            if i >= len(friend_data):
                                break
                            hobby_len = int(friend_data[i])
                            i += 1
                            if i + hobby_len > len(friend_data):
                                break
                            hobby_bytes = bytes([int(friend_data[i + j]) for j in range(hobby_len)])
                            hobby_str = hobby_bytes.decode("ascii", "ignore")
                            hobbies.append(hobby_str)
                            i += hobby_len
                        
                        person.friends[friend_id] = {
                            "home_rank": home_rank,
                            "hobbies": hobbies
                        }
                else:
                    person.friends = {}

                
                people.append(person)

                # Mode of transport
                mot_desc = mode_of_transport_description_list[k].decode()
                mot_is_public = mode_of_transport_is_public_list[k]
                if mot_desc == " ":
                    person.mode_of_transport = None
                else:
                    person.mode_of_transport = ModeOfTransport(
                        description=mot_desc,
                        is_public=mot_is_public,
                    )

                # Sectors, sub-sectors, lockdown status
                raw_sector = sectors[k].decode()
                raw_sub_sector = sub_sectors[k].decode()
                raw_lockdown = lockdown_status[k].decode()

                person.sector = None if raw_sector == " " else raw_sector
                person.sub_sector = None if raw_sub_sector == " " else raw_sub_sector
                person.lockdown_status = None if raw_lockdown == " " else raw_lockdown

                # Convert each person's list of byte-string hobbies to normal Python strings
                raw_hobby_list = hobbies_data[k]  # e.g. np.array([b"reading", b"gaming"], dtype='S50')
                hobby_list = [h.decode("ascii") for h in raw_hobby_list]
                person.hobbies = hobby_list
                
                """ # Set sexual relationship data
                # 1. Relationship status
                rel_type = relationship_status_type_data[k].decode()
                rel_cheating = relationship_status_cheating_data[k]
                person.relationship_status = {
                    "type": rel_type,
                    "cheating": rel_cheating
                }
                
                # 2. Sexual orientation
                orient_type = sexual_orientation_type_data[k].decode()
                person.sexual_orientation = {
                    "orientation": orient_type
                }
                
                # 3. Sexual risk profile
                risk_level = sexual_risk_profile_level_data[k].decode()
                protection = sexual_risk_profile_protection_data[k]
                testing = sexual_risk_profile_testing_data[k]
                person.sexual_risk_profile = {
                    "level": risk_level,
                    "protection_usage": protection,
                    "testing_frequency": testing
                }
                
                # 4. Sexual partners - using the new terminology
                person.sexual_partners = {
                    "exclusive": set(exclusive_partners_data[k].tolist()),
                    "non_exclusive": set(non_exclusive_partners_data[k].tolist())
                } """

    return Population(people)


def restore_population_properties_from_hdf5(
    world: World,
    file_path: str,
    chunk_size=50000,
    domain_super_areas=None,
    super_areas_to_domain_dict: dict = None,
):
    """
    Restores additional properties of the population (e.g. groups, subgroups, area, etc.)
    from the HDF5 file. Also restores friends from stored flattened [friend_id, home_rank] arrays.

    This assumes that the People themselves already exist in `world.people`,
    so we retrieve each Person by ID and update its properties.
    """
    logger.info("restoring population...")

    activities_fields = Activities.__fields__
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        population = f["population"]
        n_people = population.attrs["n_people"]

        # Number of chunks
        n_chunks = int(np.ceil(n_people / chunk_size))

        for chunk in range(n_chunks):
            logger.info(f"Restored chunk {chunk+1} of {n_chunks}")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_people)
            length = idx2 - idx1

            # -- Read chunked datasets --
            ids = read_dataset(population["id"], idx1, idx2)
            group_ids = read_dataset(population["group_ids"], idx1, idx2)
            group_specs = read_dataset(population["group_specs"], idx1, idx2)
            subgroup_types = read_dataset(population["subgroup_types"], idx1, idx2)
            group_super_areas = read_dataset(population["group_super_areas"], idx1, idx2)
            areas = read_dataset(population["area"], idx1, idx2)
            super_areas = read_dataset(population["super_area"], idx1, idx2)
            work_super_areas = read_dataset(population["work_super_area"], idx1, idx2)
            work_super_areas_coords = read_dataset(
                population["work_super_area_coords"], idx1, idx2
            )
            work_super_areas_cities = read_dataset(
                population["work_super_area_city"], idx1, idx2
            )
            friends_chunk = population["friends"][idx1:idx2]
            hobbies_chunk = population["hobbies"][idx1:idx2]
            
            # Read sexual relationships data for restoration
            # Read partner data with the new naming convention
            """ exclusive_partners_chunk = population["exclusive_partners"][idx1:idx2]
            non_exclusive_partners_chunk = population["non_exclusive_partners"][idx1:idx2] """
            
            # -- Iterate over each person in this chunk --
            for k in range(length):
                # If we are constraining by domain_super_areas, skip if out-of-domain
                if domain_super_areas is not None:
                    person_super_area = super_areas[k]
                    if person_super_area == nan_integer:
                        raise ValueError(
                            "If `domain_super_areas` is specified, we expect non-None super areas."
                        )
                    if person_super_area not in domain_super_areas:
                        # Skip setting properties for this person
                        continue

                # Get the person from the world
                person_id = ids[k]
                person = world.people.get_from_id(person_id)

                if person:
                    # Restore friend relationships as dictionary {friend_id: {"home_rank": rank, "hobbies": [...]}}
                    friend_data = friends_chunk[k]  # Mixed data array
                    if len(friend_data) > 0:
                        # Parse the mixed data structure
                        person.friends = {}
                        i = 0
                        while i < len(friend_data):
                            if i + 2 >= len(friend_data):
                                break
                            
                            friend_id = int(friend_data[i])
                            home_rank = int(friend_data[i + 1])
                            num_hobbies = int(friend_data[i + 2])
                            i += 3
                            
                            # Read hobbies
                            hobbies = []
                            for _ in range(num_hobbies):
                                if i >= len(friend_data):
                                    break
                                hobby_len = int(friend_data[i])
                                i += 1
                                if i + hobby_len > len(friend_data):
                                    break
                                hobby_bytes = bytes([int(friend_data[i + j]) for j in range(hobby_len)])
                                hobby_str = hobby_bytes.decode("ascii", "ignore")
                                hobbies.append(hobby_str)
                                i += hobby_len
                            
                            person.friends[friend_id] = {
                                "home_rank": home_rank,
                                "hobbies": hobbies
                            }
                    else:
                        person.friends = {}

                        
                    # Restore sexual relationship partners using the new terminology
                    # Note: these relationships need to be restored even if we already have the person instance
                    """ exclusive_partners = exclusive_partners_chunk[k].tolist()
                    non_exclusive_partners = non_exclusive_partners_chunk[k].tolist()
                    
                    # Initialize sexual_partners attribute if not already present
                    if not hasattr(person, "sexual_partners") or not isinstance(person.sexual_partners, dict):
                        person.sexual_partners = {
                            "exclusive": set(),
                            "non_exclusive": set()
                        }
                    
                    # Set all partner relationships
                    person.sexual_partners["exclusive"] = set(exclusive_partners)
                    person.sexual_partners["non_exclusive"] = set(non_exclusive_partners) """

                # 2) Restore area
                area_id = areas[k]
                person.area = world.areas.get_from_id(area_id)
                person.area.people.append(person)  # maintain area->people link

                # 3) Restore work super area
                work_super_area_id = work_super_areas[k]
                if work_super_area_id == nan_integer:
                    person.work_super_area = None
                else:
                    # If in-domain or not restricting by domain
                    if (domain_super_areas is None) or (work_super_area_id in domain_super_areas):
                        ws_area = world.super_areas.get_from_id(work_super_area_id)
                        person.work_super_area = ws_area
                        # Check city match
                        if ws_area.city is not None:
                            assert ws_area.city.id == work_super_areas_cities[k]
                        ws_area.workers.append(person)
                    else:
                        # It's an external super area
                        external_domain = super_areas_to_domain_dict[work_super_area_id]
                        ext_ws_area = ExternalSuperArea(
                            domain_id=external_domain,
                            id=work_super_area_id,
                            coordinates=work_super_areas_coords[k],
                        )
                        if work_super_areas_cities[k] == nan_integer:
                            ext_ws_area.city = None
                        else:
                            ext_ws_area.city = world.cities.get_from_id(work_super_areas_cities[k])
                        person.work_super_area = ext_ws_area

                # 4) Restore groups and subgroups
                subgroups_instances = Activities(None, None, None, None, None, None)
                for i, (g_id, stype, g_spec, g_super_area) in enumerate(
                    zip(
                        group_ids[k],
                        subgroup_types[k],
                        group_specs[k],
                        group_super_areas[k],
                    )
                ):
                    if g_id == nan_integer:
                        continue
                    # decode if needed
                    group_spec_str = g_spec.decode()
                    supergroup = getattr(world, spec_mapper[group_spec_str])

                    # in-domain?
                    if domain_super_areas is None or (g_super_area in domain_super_areas):
                        group = supergroup.get_from_id(g_id)
                        assert group.id == g_id
                        subgroup = group[stype]
                        subgroup.append(person)
                        setattr(subgroups_instances, activities_fields[i], subgroup)
                    else:
                        # external group
                        domain_of_subgroup = super_areas_to_domain_dict[g_super_area]
                        group = ExternalGroup(
                            domain_id=domain_of_subgroup,
                            id=g_id,
                            spec=group_spec_str,
                        )
                        subgroup_external = ExternalSubgroup(
                            group=group,
                            subgroup_type=stype,
                        )
                        setattr(subgroups_instances, activities_fields[i], subgroup_external)

                person.subgroups = subgroups_instances


                # Restore hobbies
                raw_hobby_list = hobbies_chunk[k]  # e.g. np.array([b"reading", b"gaming"], dtype='S50')
                # decode each hobby
                hobby_list = [h.decode("ascii") for h in raw_hobby_list]
                person.hobbies = hobby_list
                
                # Need to ensure the person has the sexual relationship data from the load_population_from_hdf5 function
                # We don't need to read it again from the file, as it was already loaded during population loading
                # This is just to make sure the sexual relationship data is completely preserved even in multi-domain scenarios

    logger.info("population restored successfully.")