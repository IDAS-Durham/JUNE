import h5py
import random
import logging
from collections import defaultdict
from copy import copy, deepcopy

from june.groups import Household
from june.geography import Geography
from june.world import World
from june.groups import Cemeteries, Households
from . import (
    load_geography_from_hdf5,
    load_hospitals_from_hdf5,
    load_schools_from_hdf5,
    load_companies_from_hdf5,
    load_population_from_hdf5,
    load_care_homes_from_hdf5,
    load_households_from_hdf5,
    load_universities_from_hdf5,
    load_stations_from_hdf5,
    load_cities_from_hdf5,
    load_social_venues_from_hdf5,
    save_geography_to_hdf5,
    save_population_to_hdf5,
    save_schools_to_hdf5,
    save_hospitals_to_hdf5,
    save_companies_to_hdf5,
    save_universities_to_hdf5,
    save_cities_to_hdf5,
    save_stations_to_hdf5,
    save_care_homes_to_hdf5,
    save_social_venues_to_hdf5,
    save_households_to_hdf5,
    save_data_for_domain_decomposition,
    restore_population_properties_from_hdf5,
    restore_households_properties_from_hdf5,
    restore_care_homes_properties_from_hdf5,
    restore_cities_and_stations_properties_from_hdf5,
    restore_geography_properties_from_hdf5,
    restore_companies_properties_from_hdf5,
    restore_school_properties_from_hdf5,
    restore_social_venues_properties_from_hdf5,
    restore_universities_properties_from_hdf5,
    restore_hospital_properties_from_hdf5,
)
from june.demography import Population
from june.demography.person import Activities, Person
from june.mpi_setup import mpi_rank

logger = logging.getLogger("world_saver")
if mpi_rank > 0:
    logger.propagate = False


def save_world_to_hdf5(world: World, file_path: str, chunk_size=100000):
    """
    Saves the world to an hdf5 file. All supergroups and geography
    are stored as groups. Class instances are substituted by ids of the 
    instances. To load the world back, one needs to call the
    generate_world_from_hdf5 function.

    Parameters
    ----------
    file_path
        path of the hdf5 file
    chunk_size
        how many units of supergroups to process at a time.
        It is advise to keep it around 1e5
    """
    logger.info("saving world to HDF5")
    # empty file
    with h5py.File(file_path, "w"):
        pass
    geo = Geography(world.areas, world.super_areas, world.regions)
    save_geography_to_hdf5(geo, file_path)
    logger.info("saving population...")
    save_population_to_hdf5(world.people, file_path, chunk_size)
    if world.hospitals is not None:
        logger.info("saving hospitals...")
        save_hospitals_to_hdf5(world.hospitals, file_path, chunk_size)
    if world.schools is not None:
        logger.info("saving schools...")
        save_schools_to_hdf5(world.schools, file_path, chunk_size)
    if world.companies is not None:
        logger.info("saving companies...")
        save_companies_to_hdf5(world.companies, file_path, chunk_size)
    if world.households is not None:
        logger.info("saving households...")
        save_households_to_hdf5(world.households, file_path, chunk_size)
    if world.care_homes is not None:
        logger.info("saving care homes...")
        save_care_homes_to_hdf5(world.care_homes, file_path, chunk_size)
    if world.cities is not None:
        logger.info("saving cities...")
        save_cities_to_hdf5(world.cities, file_path)
    if world.stations is not None:
        logger.info("saving stations...")
        save_stations_to_hdf5(world.stations, file_path)
    if world.universities is not None:
        logger.info("saving universities...")
        save_universities_to_hdf5(world.universities, file_path)
    social_venue_possible_specs = ["pubs", "groceries", "cinemas", "gyms"]  # TODO: generalise
    social_venues_list = []
    for spec in social_venue_possible_specs:
        if hasattr(world, spec) and getattr(world, spec) is not None:
            social_venues_list.append(getattr(world, spec))
    if social_venues_list:
        logger.info(f"saving social venues...")
        save_social_venues_to_hdf5(social_venues_list, file_path)
    logger.info("Saving domain decomposition data...")
    save_data_for_domain_decomposition(world, file_path)



def generate_world_from_hdf5(file_path: str, chunk_size=500000) -> World:
    """
    Loads the world from an hdf5 file. All id references are substituted
    by actual references to the relevant instances.
    Parameters
    ----------
    file_path
        path of the hdf5 file
    chunk_size
        how many units of supergroups to process at a time.
        It is advise to keep it around 1e6
    """
    logger.info("loading world from HDF5")
    world = World()
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        f_keys = list(f.keys()).copy()
    geography = load_geography_from_hdf5(file_path=file_path, chunk_size=chunk_size)
    world.areas = geography.areas
    world.super_areas = geography.super_areas
    world.regions = geography.regions
    if "hospitals" in f_keys:
        logger.info("loading hospitals...")
        world.hospitals = load_hospitals_from_hdf5(
            file_path=file_path, chunk_size=chunk_size
        )
    if "schools" in f_keys:
        logger.info("loading schools...")
        world.schools = load_schools_from_hdf5(
            file_path=file_path, chunk_size=chunk_size
        )
    if "companies" in f_keys:
        world.companies = load_companies_from_hdf5(
            file_path=file_path, chunk_size=chunk_size
        )
    if "care_homes" in f_keys:
        logger.info("loading care homes...")
        world.care_homes = load_care_homes_from_hdf5(
            file_path=file_path, chunk_size=chunk_size
        )
    if "universities" in f_keys:
        logger.info("loading universities...")
        world.universities = load_universities_from_hdf5(
            file_path=file_path, chunk_size=chunk_size
        )
    if "cities" in f_keys:
        logger.info("loading cities...")
        world.cities = load_cities_from_hdf5(file_path)
    if "stations" in f_keys:
        logger.info("loading stations...")
        (
            world.stations,
            world.inter_city_transports,
            world.city_transports,
        ) = load_stations_from_hdf5(file_path)
    if "households" in f_keys:
        world.households = load_households_from_hdf5(file_path, chunk_size=chunk_size)
    if "population" in f_keys:
        world.people = load_population_from_hdf5(file_path, chunk_size=chunk_size)
    if "social_venues" in f_keys:
        logger.info("loading social venues...")
        social_venues_dict = load_social_venues_from_hdf5(file_path)
        for social_venues_spec, social_venues in social_venues_dict.items():
            setattr(world, social_venues_spec, social_venues)

    # restore world
    logger.info("restoring world...")
    restore_geography_properties_from_hdf5(
        world=world, file_path=file_path, chunk_size=chunk_size
    )
    if "population" in f_keys:
        restore_population_properties_from_hdf5(
            world=world, file_path=file_path, chunk_size=chunk_size
        )
    if "households" in f_keys:
        restore_households_properties_from_hdf5(
            world=world, file_path=file_path, chunk_size=chunk_size
        )
    if "care_homes" in f_keys:
        logger.info("restoring care homes...")
        restore_care_homes_properties_from_hdf5(
            world=world, file_path=file_path, chunk_size=chunk_size
        )
    if "hospitals" in f_keys:
        logger.info("restoring hospitals...")
        restore_hospital_properties_from_hdf5(
            world=world, file_path=file_path, chunk_size=chunk_size
        )
    if "cities" and "stations" in f_keys:
        logger.info("restoring commute...")
        restore_cities_and_stations_properties_from_hdf5(
            world=world, file_path=file_path, chunk_size=chunk_size
        )
    if "companies" in f_keys:
        logger.info("restoring companies...")
        restore_companies_properties_from_hdf5(
            world=world, file_path=file_path, chunk_size=chunk_size,
        )
    if "schools" in f_keys:
        logger.info("restoring schools...")
        restore_school_properties_from_hdf5(
            world=world, file_path=file_path, chunk_size=chunk_size,
        )
    if "universities" in f_keys:
        logger.info("restoring unis...")
        restore_universities_properties_from_hdf5(world=world, file_path=file_path)

    if "social_venues" in f_keys:
        logger.info("restoring social venues...")
        restore_social_venues_properties_from_hdf5(world=world, file_path=file_path)
    world.cemeteries = Cemeteries()
    return world


def generate_domain_from_hdf5(
    domain_id, super_areas_to_domain_dict: dict, file_path: str, chunk_size=500000
) -> "Domain":
    """
    Loads the world from an hdf5 file. All id references are substituted
    by actual references to the relevant instances.
    Parameters
    ----------
    file_path
        path of the hdf5 file
    chunk_size
        how many units of supergroups to process at a time.
        It is advise to keep it around 1e6
    """
    logger.info(f"loading domain {domain_id} from HDF5")
    # import here to avoid recurisve imports
    from june.domains import Domain

    # get the super area ids of this domain
    super_area_ids = set()
    for super_area, did in super_areas_to_domain_dict.items():
        if did == domain_id:
            super_area_ids.add(super_area)
    domain = Domain()
    # get keys in hdf5 file
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        f_keys = list(f.keys()).copy()
    geography = load_geography_from_hdf5(
        file_path=file_path, chunk_size=chunk_size, domain_super_areas=super_area_ids
    )
    domain.areas = geography.areas
    area_ids = set([area.id for area in domain.areas])
    domain.super_areas = geography.super_areas
    domain.regions = geography.regions

    # load world data
    if "hospitals" in f_keys:
        logger.info("loading hospitals...")
        domain.hospitals = load_hospitals_from_hdf5(
            file_path=file_path,
            chunk_size=chunk_size,
            domain_super_areas=super_area_ids,
            super_areas_to_domain_dict=super_areas_to_domain_dict,
        )
    if "schools" in f_keys:
        logger.info("loading schools...")
        domain.schools = load_schools_from_hdf5(
            file_path=file_path,
            chunk_size=chunk_size,
            domain_super_areas=super_area_ids,
        )
    if "companies" in f_keys:
        domain.companies = load_companies_from_hdf5(
            file_path=file_path,
            chunk_size=chunk_size,
            domain_super_areas=super_area_ids,
        )
    if "care_homes" in f_keys:
        logger.info("loading care homes...")
        domain.care_homes = load_care_homes_from_hdf5(
            file_path=file_path,
            chunk_size=chunk_size,
            domain_super_areas=super_area_ids,
        )
    if "universities" in f_keys:
        logger.info("loading universities...")
        domain.universities = load_universities_from_hdf5(
            file_path=file_path, chunk_size=chunk_size, domain_areas=area_ids,
        )
    if "cities" in f_keys:
        logger.info("loading cities...")
        domain.cities = load_cities_from_hdf5(
            file_path=file_path,
            domain_super_areas=super_area_ids,
            super_areas_to_domain_dict=super_areas_to_domain_dict,
        )
    if "stations" in f_keys:
        logger.info("loading stations...")
        (
            domain.stations,
            domain.inter_city_transports,
            domain.city_transports,
        ) = load_stations_from_hdf5(
            file_path,
            domain_super_areas=super_area_ids,
            super_areas_to_domain_dict=super_areas_to_domain_dict,
        )
    if "households" in f_keys:
        domain.households = load_households_from_hdf5(
            file_path, chunk_size=chunk_size, domain_super_areas=super_area_ids
        )
    if "population" in f_keys:
        domain.people = load_population_from_hdf5(
            file_path, chunk_size=chunk_size, domain_super_areas=super_area_ids
        )
    if "social_venues" in f_keys:
        logger.info("loading social venues...")
        social_venues_dict = load_social_venues_from_hdf5(
            file_path, domain_areas=area_ids
        )
        for social_venues_spec, social_venues in social_venues_dict.items():
            setattr(domain, social_venues_spec, social_venues)

    # restore world
    logger.info("restoring world...")
    restore_geography_properties_from_hdf5(
        world=domain,
        file_path=file_path,
        chunk_size=chunk_size,
        domain_super_areas=super_area_ids,
        super_areas_to_domain_dict=super_areas_to_domain_dict,
    )
    if "population" in f_keys:
        restore_population_properties_from_hdf5(
            world=domain,
            file_path=file_path,
            chunk_size=chunk_size,
            domain_super_areas=super_area_ids,
            super_areas_to_domain_dict=super_areas_to_domain_dict,
        )
    if "households" in f_keys:
        restore_households_properties_from_hdf5(
            world=domain,
            file_path=file_path,
            chunk_size=chunk_size,
            domain_super_areas=super_area_ids,
            super_areas_to_domain_dict=super_areas_to_domain_dict
        )
    if "care_homes" in f_keys:
        logger.info("restoring care homes...")
        restore_care_homes_properties_from_hdf5(
            world=domain,
            file_path=file_path,
            chunk_size=chunk_size,
            domain_super_areas=super_area_ids,
        )
    if "hospitals" in f_keys:
        logger.info("restoring hospitals...")
        restore_hospital_properties_from_hdf5(
            world=domain,
            file_path=file_path,
            chunk_size=chunk_size,
            domain_super_areas=super_area_ids,
            domain_areas=area_ids,
            super_areas_to_domain_dict=super_areas_to_domain_dict,
        )
    if "companies" in f_keys:
        logger.info("restoring companies...")
        restore_companies_properties_from_hdf5(
            world=domain,
            file_path=file_path,
            chunk_size=chunk_size,
            domain_super_areas=super_area_ids,
        )
    if "schools" in f_keys:
        logger.info("restoring schools...")
        restore_school_properties_from_hdf5(
            world=domain,
            file_path=file_path,
            chunk_size=chunk_size,
            domain_super_areas=super_area_ids,
        )
    if "universities" in f_keys:
        logger.info("restoring unis...")
        restore_universities_properties_from_hdf5(
            world=domain, file_path=file_path, domain_areas=area_ids
        )

    if "cities" and "stations" in f_keys:
        logger.info("restoring commute...")
        restore_cities_and_stations_properties_from_hdf5(
            world=domain,
            file_path=file_path,
            chunk_size=chunk_size,
            domain_super_areas=super_area_ids,
            super_areas_to_domain_dict=super_areas_to_domain_dict,
        )

    if "social_venues" in f_keys:
        logger.info("restoring social venues...")
        restore_social_venues_properties_from_hdf5(
            world=domain, file_path=file_path, domain_areas=area_ids
        )
    domain.cemeteries = Cemeteries()
    return domain
