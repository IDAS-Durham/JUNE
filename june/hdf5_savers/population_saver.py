from june.groups.commute import CommuteCity
from june.commute import ModeOfTransport
from june.demography import Population, Person
import h5py
import numpy as np

nan_integer = -999  # only used to store/load hdf5 integer arrays with inf/nan values


def save_population_to_hdf5(
    population: Population, file_path: str, chunk_size: int = 100000
):
    """
    Saves the Population object to hdf5 format file ``file_path``. Currently for each person,
    the following values are stored:
    - id, age, sex, ethnicity, area, subgroup memberships ids, housemate ids, mode_of_transport,
      home_city

    Parameters
    ----------
    population
        population object
    file_path
        path of the saved hdf5 file
    chunk_size
        number of people to save at a time. Note that they have to be copied to be saved,
        so keep the number below 1e6.
    """
    n_people = len(population.people)
    n_chunks = int(np.ceil(n_people / chunk_size))
    with h5py.File(file_path, "a") as f:
        people_dset = f.create_group("population")
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_people)
            ids = []
            ages = []
            sexes = []
            ethns = []
            socioecon_indices = []
            areas = []
            sectors = []
            sub_sectors = []
            group_ids = []
            group_specs = []
            subgroup_types = []
            home_city = []
            mode_of_transport_description = []
            mode_of_transport_is_public = []
            lockdown_status = []

            for person in population.people[idx1:idx2]:
                ids.append(person.id)
                ages.append(person.age)
                sexes.append(person.sex.encode("ascii", "ignore"))
                if person.ethnicity is None:
                    ethns.append(" ".encode("ascii", "ignore"))
                else:
                    ethns.append(person.ethnicity.encode("ascii", "ignore"))
                if person.socioecon_index is None:
                    socioecon_indices.append(nan_integer)
                else:
                    socioecon_indices.append(person.socioecon_index)
                if person.home_city is None:
                    home_city.append(nan_integer)
                else:
                    home_city.append(person.home_city.id)
                if person.area is not None:
                    areas.append(person.area.id)
                else:
                    areas.append(nan_integer)
                if person.sector is None:
                    sectors.append(" ".encode("ascii", "ignore"))
                else:
                    sectors.append(person.sector.encode("ascii", "ignore"))
                if person.sub_sector is None:
                    sub_sectors.append(" ".encode("ascii", "ignore"))
                else:
                    sub_sectors.append(person.sub_sector.encode("ascii", "ignore"))
                if person.lockdown_status is None:
                    lockdown_status.append(" ".encode("ascii", "ignore"))
                else:
                    lockdown_status.append(
                        person.lockdown_status.encode("ascii", "ignore")
                    )
                gids = []
                stypes = []
                specs = []
                for subgroup in person.subgroups.iter():
                    if subgroup is None:
                        gids.append(nan_integer)
                        stypes.append(nan_integer)
                        specs.append(" ".encode("ascii", "ignore"))
                    else:
                        gids.append(subgroup.group.id)
                        stypes.append(subgroup.subgroup_type)
                        specs.append(subgroup.group.spec.encode("ascii", "ignore"))
                group_specs.append(np.array(specs, dtype="S20"))
                group_ids.append(np.array(gids, dtype=np.int))
                subgroup_types.append(np.array(stypes, dtype=np.int))
                if person.mode_of_transport == None:
                    mode_of_transport_description.append(" ".encode("ascii", "ignore"))
                    mode_of_transport_is_public.append(False)
                else:
                    mode_of_transport_description.append(
                        person.mode_of_transport.description.encode("ascii", "ignore")
                    )
                    mode_of_transport_is_public.append(
                        person.mode_of_transport.is_public
                    )

            ids = np.array(ids, dtype=np.int)
            ages = np.array(ages, dtype=np.int)
            sexes = np.array(sexes, dtype="S10")
            ethns = np.array(ethns, dtype="S10")
            socioecon_indices = np.array(socioecon_indices, dtype=np.int)
            home_city = np.array(home_city, dtype=np.int)
            areas = np.array(areas, dtype=np.int)
            group_ids = np.array(group_ids, dtype=np.int)
            subgroup_types = np.array(subgroup_types, dtype=np.int)
            group_specs = np.array(group_specs, dtype="S20")
            sectors = np.array(sectors, dtype="S30")
            sub_sectors = np.array(sub_sectors, dtype="S30")
            mode_of_transport_description = np.array(
                mode_of_transport_description, dtype="S100"
            )
            mode_of_transport_is_public = np.array(
                mode_of_transport_is_public, dtype=np.bool
            )
            lockdown_status = np.array(lockdown_status, dtype="S20")

            if chunk == 0:
                people_dset.attrs["n_people"] = n_people
                people_dset.create_dataset("id", data=ids, maxshape=(None,))
                people_dset.create_dataset("age", data=ages, maxshape=(None,))
                people_dset.create_dataset("sex", data=sexes, maxshape=(None,))
                people_dset.create_dataset("sector", data=sectors, maxshape=(None,))
                people_dset.create_dataset(
                    "sub_sector", data=sub_sectors, maxshape=(None,)
                )
                people_dset.create_dataset(
                    "socioecon_index", data=socioecon_indices, maxshape=(None,)
                )
                people_dset.create_dataset(
                    "home_city", data=home_city, maxshape=(None,)
                )
                people_dset.create_dataset("ethnicity", data=ethns, maxshape=(None,))
                people_dset.create_dataset(
                    "group_ids", data=group_ids, maxshape=(None, group_ids.shape[1]),
                )
                people_dset.create_dataset(
                    "group_specs",
                    data=group_specs,
                    maxshape=(None, group_specs.shape[1]),
                )
                people_dset.create_dataset(
                    "subgroup_types",
                    data=subgroup_types,
                    maxshape=(None, subgroup_types.shape[1]),
                )
                people_dset.create_dataset("area", data=areas, maxshape=(None,))
                people_dset.create_dataset(
                    "mode_of_transport_description",
                    data=mode_of_transport_description,
                    maxshape=(None,),
                )
                people_dset.create_dataset(
                    "mode_of_transport_is_public",
                    data=mode_of_transport_is_public,
                    maxshape=(None,),
                )
                people_dset.create_dataset(
                    "lockdown_status", data=lockdown_status, maxshape=(None,)
                )
            else:
                newshape = (people_dset["id"].shape[0] + ids.shape[0],)
                people_dset["id"].resize(newshape)
                people_dset["id"][idx1:idx2] = ids
                people_dset["age"].resize(newshape)
                people_dset["age"][idx1:idx2] = ages
                people_dset["sex"].resize(newshape)
                people_dset["sex"][idx1:idx2] = sexes
                people_dset["ethnicity"].resize(newshape)
                people_dset["ethnicity"][idx1:idx2] = ethns
                people_dset["sector"].resize(newshape)
                people_dset["sector"][idx1:idx2] = sectors
                people_dset["sub_sector"].resize(newshape)
                people_dset["sub_sector"][idx1:idx2] = sub_sectors
                people_dset["socioecon_index"].resize(newshape)
                people_dset["socioecon_index"][idx1:idx2] = socioecon_indices
                people_dset["home_city"].resize(newshape)
                people_dset["home_city"][idx1:idx2] = home_city
                people_dset["area"].resize(newshape)
                people_dset["area"][idx1:idx2] = areas
                people_dset["group_ids"].resize(newshape[0], axis=0)
                people_dset["group_ids"][idx1:idx2] = group_ids
                people_dset["group_specs"].resize(newshape[0], axis=0)
                people_dset["group_specs"][idx1:idx2] = group_specs
                people_dset["subgroup_types"].resize(newshape[0], axis=0)
                people_dset["subgroup_types"][idx1:idx2] = subgroup_types
                people_dset["mode_of_transport_description"].resize(newshape)
                people_dset["mode_of_transport_description"][
                    idx1:idx2
                ] = mode_of_transport_description
                people_dset["mode_of_transport_is_public"].resize(newshape)
                people_dset["mode_of_transport_is_public"][
                    idx1:idx2
                ] = mode_of_transport_is_public
                people_dset["lockdown_status"].resize(newshape)
                people_dset["lockdown_status"][
                    idx1:idx2
                ] = lockdown_status


def load_population_from_hdf5(file_path: str, chunk_size=100000):
    """
    Loads the population from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    print("loading population from hdf5 ", end="")
    with h5py.File(file_path, "r") as f:
        people = list()
        population = f["population"]
        # read in chunks of 100k people
        n_people = population.attrs["n_people"]
        n_chunks = int(np.ceil(n_people / chunk_size))
        for chunk in range(n_chunks):
            print(".", end="")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_people)
            ids = population["id"][idx1:idx2]
            ages = population["age"][idx1:idx2]
            sexes = population["sex"][idx1:idx2]
            ethns = population["ethnicity"][idx1:idx2]
            socioecon_indices = population["socioecon_index"][idx1:idx2]
            home_city = population["home_city"][idx1:idx2]
            group_ids = population["group_ids"][idx1:idx2]
            group_specs = population["group_specs"][idx1:idx2]
            subgroup_types = population["subgroup_types"][idx1:idx2]
            sectors = population["sector"][idx1:idx2]
            sub_sectors = population["sub_sector"][idx1:idx2]
            lockdown_status = population["lockdown_status"][idx1:idx2]
            mode_of_transport_is_public_list = population[
                "mode_of_transport_is_public"
            ][idx1:idx2]
            mode_of_transport_description_list = population[
                "mode_of_transport_description"
            ][idx1:idx2]
            areas = population["area"][idx1:idx2]
            for k in range(idx2 - idx1):
                if ethns[k].decode() == " ":
                    ethnicity = None
                else:
                    ethnicity = ethns[k].decode()
                if socioecon_indices[k] == nan_integer:
                    socioecon_index = None
                else:
                    socioecon_index = socioecon_indices[k]
                person = Person.from_attributes(
                    id=ids[k],
                    age=ages[k],
                    sex=sexes[k].decode(),
                    ethnicity=ethnicity,
                    socioecon_index=socioecon_index,
                )
                mode_of_transport_description = mode_of_transport_description_list[k]
                mode_of_transport_is_public = mode_of_transport_is_public_list[k]
                # mode of transport
                if mode_of_transport_description.decode() == " ":
                    person.mode_of_transport = None
                else:
                    person.mode_of_transport = ModeOfTransport(
                        description=mode_of_transport_description.decode(),
                        is_public=mode_of_transport_is_public,
                    )
                hc = home_city[k]
                if hc == nan_integer:
                    person.home_city = None
                else:
                    person.home_city = hc
                subgroups = []
                for group_id, subgroup_type, group_spec in zip(
                    group_ids[k], subgroup_types[k], group_specs[k]
                ):
                    if group_id == nan_integer:
                        group_id = None
                        subgroup_type = None
                        group_spec = None
                    else:
                        group_spec = group_spec.decode()
                    subgroups.append([group_spec, group_id, subgroup_type])
                person.subgroups = subgroups
                person.area = areas[k]
                if sectors[k].decode() == " ":
                    person.sector = None
                else:
                    person.sector = sectors[k].decode()
                if sub_sectors[k].decode() == " ":
                    person.sub_sector = None
                else:
                    person.sub_sector = sub_sectors[k].decode()
                if lockdown_status[k].decode() == " ":
                    person.lockdown_status = None
                else:
                    person.lockdown_status = lockdown_status[k].decode()
                people.append(person)
    print("\n", end="")
    return Population(people)
