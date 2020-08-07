import h5py
import numpy as np
from june.groups import Household, Households
from collections import defaultdict

nan_integer = -999


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
    int_vlen_type = h5py.vlen_dtype(np.dtype("int64"))
    str_vlen_type = h5py.vlen_dtype(np.dtype("S20"))
    with h5py.File(file_path, "a") as f:
        households_dset = f.create_group("households")
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            ids = []
            areas = []
            types = []
            max_sizes = []
            household_complacencies = []
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
                household_complacencies.append(household.household_complacency)

            ids = np.array(ids, dtype=np.int)
            areas = np.array(areas, dtype=np.int)
            types = np.array(types, dtype="S15")
            max_sizes = np.array(max_sizes, dtype=np.float)
            household_complacencies = np.array(household_complacencies, dtype=np.float)
            if chunk == 0:
                households_dset.attrs["n_households"] = n_households
                households_dset.create_dataset("id", data=ids, maxshape=(None,))
                households_dset.create_dataset("area", data=areas, maxshape=(None,))
                households_dset.create_dataset("type", data=types, maxshape=(None,))
                households_dset.create_dataset(
                    "max_size", data=max_sizes, maxshape=(None,)
                )
                households_dset.create_dataset(
                    "household_complacency", data=household_complacencies, maxshape=(None,)
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
                households_dset["household_complacency"].resize(newshape)
                households_dset["household_complacency"][idx1:idx2] = household_complacencies 

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
        relatives_in_households = np.array(
            relatives_in_households, dtype=int_vlen_type
        )
        relatives_in_care_homes = np.array(
            relatives_in_care_homes, dtype=int_vlen_type
        )
        social_venues_specs_list = np.array(
            social_venues_specs_list, dtype=str_vlen_type
        )
        social_venues_ids_list = np.array(social_venues_ids_list, dtype=int_vlen_type)
        try:
            households_dset.create_dataset(
                "relatives_in_households", data=relatives_in_households,
            )
        except:
            relatives_in_households = np.array(relatives_in_households, dtype=np.int)
            households_dset.create_dataset(
                "relatives_in_households", data=relatives_in_households,
            )
        try:
            households_dset.create_dataset(
                "relatives_in_care_homes", data=relatives_in_care_homes,
            )
        except:
            relatives_in_care_homes = np.array(relatives_in_care_homes, dtype=np.int)
            households_dset.create_dataset(
                "relatives_in_care_homes", data=relatives_in_care_homes,
            )
        households_dset.create_dataset(
            "social_venues_specs", data=social_venues_specs_list,
        )
        households_dset.create_dataset(
            "social_venues_ids", data=social_venues_ids_list,
        )


def load_households_from_hdf5(file_path: str, chunk_size=50000):
    """
    Loads households from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    print("loading households from hdf5 ", end="")
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        households = f["households"]
        households_list = list()
        n_households = households.attrs["n_households"]
        n_chunks = int(np.ceil(n_households / chunk_size))
        for chunk in range(n_chunks):
            print(".", end="")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_households)
            ids = households["id"][idx1:idx2]
            types = households["type"][idx1:idx2]
            areas = households["area"][idx1:idx2]
            max_sizes = households["max_size"][idx1:idx2]
            # TODO: household_complacencies = households["household_complacency"][idx1:idx2]
            relatives_in_households = households["relatives_in_households"][idx1:idx2]
            relatives_in_care_homes = households["relatives_in_care_homes"][idx1:idx2]
            social_venues_specs = households["social_venues_specs"][idx1:idx2]
            social_venues_ids = households["social_venues_ids"][idx1:idx2]
            for k in range(idx2 - idx1):
                area = areas[k]
                if area == nan_integer:
                    area = None
                type = types[k]
                if type.decode() == " ":
                    type = None
                else:
                    type = type.decode()
                household = Household(type=type, area=area, max_size=max_sizes[k],
                        household_complacency = np.random.rand()
                        # TODO: :household_complacency=household_complacencies[k]
                        )
                household.id = ids[k]
                if relatives_in_households[k][0] == nan_integer:
                    household.relatives_in_households = ()
                else:
                    household.relatives_in_households = relatives_in_households[k]
                if relatives_in_care_homes[k][0] == nan_integer:
                    household.relatives_in_care_homes = ()
                else:
                    household.relatives_in_care_homes = relatives_in_care_homes[k]
                household.social_venues = defaultdict(list)
                for sv_spec, sv_id in zip(social_venues_specs[k], social_venues_ids[k]):
                    household.social_venues[sv_spec.decode()].append(sv_id)
                households_list.append(household)
    print("\n", end="")
    return Households(households_list)
