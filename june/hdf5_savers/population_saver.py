import h5py
import numpy as np
from collections import OrderedDict
import logging


from .utils import read_dataset
from june.groups import ExternalSubgroup, ExternalGroup
from june.groups.travel import ModeOfTransport
from june.demography import Population, Person
from june.demography.person import Activities
from june.geography import ExternalSuperArea
from june.world import World
from june.mpi_setup import mpi_rank

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


def save_population_to_hdf5(
    population: Population, file_path: str, chunk_size: int = 100000
):
    """
    Saves the Population object to hdf5 format file ``file_path``. Currently for each person,
    the following values are stored:
    - id, age, sex, ethnicity, area, subgroup memberships ids, housemate ids, mode_of_transport,

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

            for person in population.people[idx1:idx2]:
                ids.append(person.id)
                ages.append(person.age)
                sexes.append(person.sex.encode("ascii", "ignore"))
                if person.ethnicity is None:
                    ethns.append(" ".encode("ascii", "ignore"))
                else:
                    ethns.append(person.ethnicity.encode("ascii", "ignore"))
                if person.area is not None:
                    areas.append(person.area.id)
                    super_areas.append(person.area.super_area.id)
                else:
                    areas.append(nan_integer)
                    super_areas.append(nan_integer)
                if person.work_super_area is not None:
                    work_super_areas.append(person.work_super_area.id)
                    work_super_area_coords.append(
                        np.array(person.work_super_area.coordinates, dtype=np.float64)
                    )
                    if person.work_super_area.city is not None:
                        work_super_areas_cities.append(person.work_super_area.city.id)
                    else:
                        work_super_areas_cities.append(nan_integer)
                else:
                    work_super_areas.append(nan_integer)
                    work_super_areas_cities.append(nan_integer)
                    work_super_area_coords.append(
                        np.array([nan_integer, nan_integer], dtype=np.float64)
                    )
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
                        if subgroup.group.super_area is None:
                            group_super_areas_temp.append(nan_integer)
                        else:
                            group_super_areas_temp.append(subgroup.group.super_area.id)
                group_specs.append(np.array(specs, dtype="S20"))
                group_ids.append(np.array(gids, dtype=np.int64))
                subgroup_types.append(np.array(stypes, dtype=np.int64))
                group_super_areas.append(np.array(group_super_areas_temp, dtype=np.int64))
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

            ids = np.array(ids, dtype=np.int64)
            ages = np.array(ages, dtype=np.int64)
            sexes = np.array(sexes, dtype="S10")
            ethns = np.array(ethns, dtype="S10")
            areas = np.array(areas, dtype=np.int64)
            super_areas = np.array(super_areas, dtype=np.int64)
            work_super_areas = np.array(work_super_areas, dtype=np.int64)
            work_super_areas_cities = np.array(work_super_areas_cities, dtype=np.int64)
            work_super_area_coords = np.array(work_super_area_coords, dtype=np.float64)
            group_ids = np.array(group_ids, dtype=np.int64)
            subgroup_types = np.array(subgroup_types, dtype=np.int64)
            group_specs = np.array(group_specs, dtype="S20")
            group_super_areas = np.array(group_super_areas, dtype=np.int64)
            sectors = np.array(sectors, dtype="S30")
            sub_sectors = np.array(sub_sectors, dtype="S30")
            mode_of_transport_description = np.array(
                mode_of_transport_description, dtype="S100"
            )
            mode_of_transport_is_public = np.array(
                mode_of_transport_is_public, dtype=bool
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
                people_dset.create_dataset(
                    "group_super_areas",
                    data=group_super_areas,
                    maxshape=(None, subgroup_types.shape[1]),
                )
                people_dset.create_dataset("area", data=areas, maxshape=(None,))
                people_dset.create_dataset(
                    "super_area", data=super_areas, maxshape=(None,)
                )
                people_dset.create_dataset(
                    "work_super_area", data=work_super_areas, maxshape=(None,)
                )
                people_dset.create_dataset(
                    "work_super_area_coords",
                    data=work_super_area_coords,
                    maxshape=(None, work_super_area_coords.shape[1]),
                )
                people_dset.create_dataset(
                    "work_super_area_city",
                    data=work_super_areas_cities,
                    maxshape=(None,),
                )
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
                people_dset["area"].resize(newshape)
                people_dset["area"][idx1:idx2] = areas
                people_dset["super_area"].resize(newshape)
                people_dset["super_area"][idx1:idx2] = super_areas
                people_dset["work_super_area"].resize(newshape)
                people_dset["work_super_area"][idx1:idx2] = work_super_areas
                people_dset["work_super_area_coords"].resize(newshape[0], axis=0)
                people_dset["work_super_area_coords"][
                    idx1:idx2
                ] = work_super_area_coords
                people_dset["work_super_area_city"].resize(newshape)
                people_dset["work_super_area_city"][idx1:idx2] = work_super_areas_cities
                people_dset["group_ids"].resize(newshape[0], axis=0)
                people_dset["group_ids"][idx1:idx2] = group_ids
                people_dset["group_specs"].resize(newshape[0], axis=0)
                people_dset["group_specs"][idx1:idx2] = group_specs
                people_dset["subgroup_types"].resize(newshape[0], axis=0)
                people_dset["subgroup_types"][idx1:idx2] = subgroup_types
                people_dset["group_super_areas"].resize(newshape[0], axis=0)
                people_dset["group_super_areas"][idx1:idx2] = group_super_areas
                people_dset["mode_of_transport_description"].resize(newshape)
                people_dset["mode_of_transport_description"][
                    idx1:idx2
                ] = mode_of_transport_description
                people_dset["mode_of_transport_is_public"].resize(newshape)
                people_dset["mode_of_transport_is_public"][
                    idx1:idx2
                ] = mode_of_transport_is_public
                people_dset["lockdown_status"].resize(newshape)
                people_dset["lockdown_status"][idx1:idx2] = lockdown_status


def load_population_from_hdf5(
    file_path: str, chunk_size=100000, domain_super_areas=None
):
    """
    Loads the population from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    people = []
    logger.info("loading population...")
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        # people = []
        population = f["population"]
        # read in chunks of 100k people
        n_people = population.attrs["n_people"]
        n_chunks = int(np.ceil(n_people / chunk_size))
        for chunk in range(n_chunks):
            logger.info(f"Loaded chunk {chunk} of {n_chunks}")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_people)
            length = idx2 - idx1
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
            for k in range(idx2 - idx1):
                if domain_super_areas is not None:
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                if ethns[k].decode() == " ":
                    ethn = None
                else:
                    ethn = ethns[k].decode()
                person = Person.from_attributes(
                    id=ids[k],
                    age=ages[k],
                    sex=sexes[k].decode(),
                    ethnicity=ethn,
                )
                people.append(person)
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
    return Population(people)


def restore_population_properties_from_hdf5(
    world: World,
    file_path: str,
    chunk_size=50000,
    domain_super_areas=None,
    super_areas_to_domain_dict: dict = None,
):
    logger.info("restoring population...")
    activities_fields = Activities.__fields__
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        # people = []
        population = f["population"]
        # read in chunks of 100k people
        n_people = population.attrs["n_people"]
        n_chunks = int(np.ceil(n_people / chunk_size))
        for chunk in range(n_chunks):
            logger.info(f"Restored chunk {chunk} of {n_chunks}")
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_people)
            length = idx2 - idx1
            ids = read_dataset(population["id"], idx1, idx2)
            group_ids = read_dataset(population["group_ids"], idx1, idx2)
            group_specs = read_dataset(population["group_specs"], idx1, idx2)
            subgroup_types = read_dataset(population["subgroup_types"], idx1, idx2)
            group_super_areas = read_dataset(
                population["group_super_areas"], idx1, idx2
            )
            areas = read_dataset(population["area"], idx1, idx2)
            super_areas = read_dataset(population["super_area"], idx1, idx2)
            work_super_areas = read_dataset(population["work_super_area"], idx1, idx2)
            work_super_areas_coords = read_dataset(population["work_super_area_coords"], idx1, idx2)
            work_super_areas_cities = read_dataset(
                population["work_super_area_city"], idx1, idx2
            )
            for k in range(length):
                if domain_super_areas is not None:
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                person = world.people.get_from_id(ids[k])
                # restore area
                person.area = world.areas.get_from_id(areas[k])
                person.area.people.append(person)
                work_super_area_id = work_super_areas[k]
                if work_super_area_id == nan_integer:
                    person.work_super_area = None
                else:
                    if (
                        domain_super_areas is None
                        or work_super_area_id in domain_super_areas
                    ):
                        person.work_super_area = world.super_areas.get_from_id(
                            work_super_area_id
                        )
                        if person.work_super_area.city is not None:
                            assert (
                                person.work_super_area.city.id
                                == work_super_areas_cities[k]
                            )
                        person.work_super_area.workers.append(person)
                    else:
                        person.work_super_area = ExternalSuperArea(
                            domain_id=super_areas_to_domain_dict[work_super_area_id],
                            id=work_super_area_id,
                            coordinates=work_super_areas_coords[k],
                        )
                        if work_super_areas_cities[k] == nan_integer:
                            person.work_super_area.city = None
                        else:
                            person.work_super_area.city = world.cities.get_from_id(
                                work_super_areas_cities[k]
                            )
                # restore groups and subgroups
                subgroups_instances = Activities(
                    None, None, None, None, None, None
                )
                for (
                    i,
                    (group_id, subgroup_type, group_spec, group_super_area),
                ) in enumerate(
                    zip(
                        group_ids[k],
                        subgroup_types[k],
                        group_specs[k],
                        group_super_areas[k],
                    )
                ):
                    if group_id == nan_integer:
                        continue
                    group_spec = group_spec.decode()
                    supergroup = getattr(world, spec_mapper[group_spec])
                    if (
                        domain_super_areas is None
                        or group_super_area in domain_super_areas
                    ):
                        group = supergroup.get_from_id(group_id)
                        assert group_id == group.id
                        subgroup = group[subgroup_type]
                        subgroup.append(person)
                        setattr(subgroups_instances, activities_fields[i], subgroup)
                    else:
                        domain_of_subgroup = super_areas_to_domain_dict[
                            group_super_area
                        ]
                        group = ExternalGroup(
                            domain_id=domain_of_subgroup, id=group_id, spec=group_spec
                        )
                        subgroup_external = ExternalSubgroup(
                            group=group, subgroup_type=subgroup_type,
                        )
                        setattr(
                            subgroups_instances, activities_fields[i], subgroup_external
                        )
                person.subgroups = subgroups_instances
