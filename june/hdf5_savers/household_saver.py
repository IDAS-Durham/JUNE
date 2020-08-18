import h5py
import numpy as np
from june.world import World
from june.groups import Household, Households
from collections import defaultdict, OrderedDict
from itertools import chain

nan_integer = -999

social_venues_spec_mapper = {
    "pubs": "pubs",
    "household_visits": "households",
    "care_home_visits": "care_homes",
    "cinemas": "cinemas",
    "groceries": "groceries",
}

int_vlen_type = h5py.vlen_dtype(np.dtype("int64"))
str_vlen_type = h5py.vlen_dtype(np.dtype("S20"))


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
            types = []
            max_sizes = []
            for household in households[idx1:idx2]:
                ids.append(household.id)
                if household.area is None:
                    areas.append(nan_integer)
                else:
                    areas.append(household.area.id)
                if household.type is None:
                    types.append(" ".encode("ascii", "ignore"))
                else:
                    types.append(household.type.encode("ascii", "ignore"))
                max_sizes.append(household.max_size)

            ids = np.array(ids, dtype=np.int)
            areas = np.array(areas, dtype=np.int)
            types = np.array(types, dtype="S20")
            max_sizes = np.array(max_sizes, dtype=np.float)
            if chunk == 0:
                households_dset.attrs["n_households"] = n_households
                households_dset.create_dataset("id", data=ids, maxshape=(None,))
                households_dset.create_dataset("area", data=areas, maxshape=(None,))
                households_dset.create_dataset("type", data=types, maxshape=(None,))
                households_dset.create_dataset(
                    "max_size", data=max_sizes, maxshape=(None,)
                )

            else:
                newshape = (households_dset["id"].shape[0] + ids.shape[0],)
                households_dset["id"].resize(newshape)
                households_dset["id"][idx1:idx2] = ids
                households_dset["area"].resize(newshape)
                households_dset["area"][idx1:idx2] = areas
                households_dset["type"].resize(newshape)
                households_dset["type"][idx1:idx2] = types
                households_dset["max_size"].resize(newshape)
                households_dset["max_size"][idx1:idx2] = max_sizes

        # I dont know how to chunk these...
        relatives_in_households = []
        relatives_in_care_homes = []
        social_venues_specs_list = []
        social_venues_ids_list = []
        for household in households:
            if (
                household.relatives_in_households is None
                or len(household.relatives_in_households) == 0
            ):
                relatives_in_households.append(np.array([nan_integer], dtype=np.int))
            else:
                relatives_in_households.append(
                    np.array(
                        [person.id for person in household.relatives_in_households],
                        dtype=np.int,
                    )
                )
            if (
                household.relatives_in_care_homes is None
                or len(household.relatives_in_care_homes) == 0
            ):
                relatives_in_care_homes.append(np.array([nan_integer], dtype=np.int))
            else:
                relatives_in_care_homes.append(
                    np.array(
                        [person.id for person in household.relatives_in_care_homes],
                        dtype=np.int,
                    )
                )
            social_venues_ids = []
            social_venues_specs = []
            for spec in household.social_venues.keys():
                for social_venue in household.social_venues[spec]:
                    social_venues_specs.append(spec.encode("ascii", "ignore"))
                    social_venues_ids.append(social_venue.id)
            social_venues_specs_list.append(np.array(social_venues_specs, dtype="S20"))
            social_venues_ids_list.append(np.array(social_venues_ids, dtype=np.int))
        relatives_in_care_homes = np.array(relatives_in_care_homes, dtype=int_vlen_type)
        social_venues_specs_list = np.array(
            social_venues_specs_list, dtype=str_vlen_type
        )
        social_venues_ids_list = np.array(social_venues_ids_list, dtype=int_vlen_type)
        if len(np.unique(list(chain(*relatives_in_households)))) > 1:
            relatives_in_households = np.array(
                relatives_in_households, dtype=int_vlen_type
            )
            households_dset.create_dataset(
                "relatives_in_households", data=relatives_in_households,
            )
        if len(np.unique(list(chain(*relatives_in_care_homes)))) > 1:
            relatives_in_care_homes = np.array(
                relatives_in_care_homes, dtype=int_vlen_type
            )
            households_dset.create_dataset(
                "relatives_in_care_homes", data=relatives_in_care_homes,
            )
        if social_venues_specs and social_venues_ids:
            households_dset.create_dataset(
                "social_venues_specs", data=social_venues_specs_list,
            )
            households_dset.create_dataset(
                "social_venues_ids", data=social_venues_ids_list,
            )


def load_households_from_hdf5(file_path: str, chunk_size=50000, for_simulation=False):
    """
    Loads households from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    print("loading households from hdf5 ", end="")
    households_list = []
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        households = f["households"]
        n_households = households.attrs["n_households"]
        n_chunks = int(np.ceil(n_households / chunk_size))
        for chunk in range(n_chunks):
            print(".", end="")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            length = idx2 - idx1
            ids = np.empty(length, dtype=int)
            types = np.empty(length, dtype="S20")
            max_sizes = np.empty(length, dtype=float)
            households["id"].read_direct(ids, np.s_[idx1:idx2], np.s_[0:length])
            households["type"].read_direct(types, np.s_[idx1:idx2], np.s_[0:length])
            households["max_size"].read_direct(
                max_sizes, np.s_[idx1:idx2], np.s_[0:length]
            )
            for k in range(length):
                if for_simulation:
                    household = Household(area=None, type=None, max_size=None)
                else:
                    household = Household(
                        area=None, type=types[k].decode(), max_size=max_sizes[k]
                    )
                households_list.append(household)
                household.id = ids[k]
    print("\n", end="")
    return Households(households_list)


def restore_households_properties_from_hdf5(
    world: World, file_path: str, chunk_size=50000, for_simulation=False
):
    """
    Loads households from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    print("loading households from hdf5 ", end="")
    first_area_id = world.areas[0].id
    first_household_id = world.households[0].id
    first_person_id = world.people[0].id
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        households = f["households"]
        n_households = households.attrs["n_households"]
        n_chunks = int(np.ceil(n_households / chunk_size))
        for chunk in range(n_chunks):
            print(".", end="")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            length = idx2 - idx1
            ids = np.empty(length, dtype=int)
            relatives_in_households_list = np.empty(length, dtype=int_vlen_type)
            relatives_in_care_homes_list = np.empty(length, dtype=int_vlen_type)
            areas = np.empty(length, dtype=np.int)
            social_venues_specs = np.empty(length, dtype=str_vlen_type)
            social_venues_ids = np.empty(length, dtype=int_vlen_type)
            households["id"].read_direct(ids, np.s_[idx1:idx2], np.s_[0:length])
            households["area"].read_direct(areas, np.s_[idx1:idx2], np.s_[0:length])
            if "relatives_in_households" in households:
                households["relatives_in_households"].read_direct(
                    relatives_in_households_list, np.s_[idx1:idx2], np.s_[0:length]
                )
            if "relatives_in_care_homes" in households:
                households["relatives_in_care_homes"].read_direct(
                    relatives_in_care_homes_list, np.s_[idx1:idx2], np.s_[0:length]
                )
            if (
                "social_venues_specs" in households
                and "social_venues_ids" in households
            ):
                households["social_venues_specs"].read_direct(
                    social_venues_specs, np.s_[idx1:idx2], np.s_[0:length]
                )
                households["social_venues_ids"].read_direct(
                    social_venues_ids, np.s_[idx1:idx2], np.s_[0:length]
                )
            for k in range(length):
                household = world.households[ids[k] - first_household_id]
                area = world.areas[areas[k] - first_area_id]
                household.area = area
                area.households.append(household)
                household.residents = tuple(household.people)
                # relatives
                if "relatives_in_households" in households:
                    if (
                        relatives_in_households_list[k][0] == nan_integer
                        or for_simulation
                    ):
                        household.household_relatives = None
                    else:
                        household_relatives = []
                        for relative in relatives_in_households_list[k]:
                            household_relatives.append(
                                world.people[relative - first_person_id]
                            )
                        household.relatives_in_households = tuple(household_relatives)
                if "relatives_in_care_homes" in households:
                    if (
                        relatives_in_care_homes_list[k][0] == nan_integer
                        or for_simulation
                    ):
                        household.care_home_relatives = None
                    else:
                        care_home_relatives = []
                        for relative in relatives_in_care_homes_list[k]:
                            care_home_relatives.append(
                                world.people[relative - first_person_id]
                            )
                        household.relatives_in_care_homes = tuple(care_home_relatives)
                # social venues
                if (
                    "social_venues_specs" in households
                    and "social_venues_ids" in households
                ):
                    for group_spec, group_id in zip(
                        social_venues_specs[k], social_venues_ids[k]
                    ):
                        spec = group_spec.decode()
                        spec_mapped = social_venues_spec_mapper[spec]
                        supergroup = getattr(world, spec_mapped)
                        first_group_id = supergroup.members[0].id
                        group = supergroup.members[group_id - first_group_id]
                        household.social_venues[spec] = (
                            *household.social_venues[spec],
                            group,
                        )
    print("\n", end="")
