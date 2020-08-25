import h5py
import random
import logging
from collections import defaultdict
from copy import copy, deepcopy

from june.groups import Household
from june.demography.geography import Geography
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
    load_commute_hubs_from_hdf5,
    load_commute_cities_from_hdf5,
    load_social_venues_from_hdf5,
    save_geography_to_hdf5,
    save_population_to_hdf5,
    save_schools_to_hdf5,
    save_hospitals_to_hdf5,
    save_companies_to_hdf5,
    save_universities_to_hdf5,
    save_commute_cities_to_hdf5,
    save_commute_hubs_to_hdf5,
    save_care_homes_to_hdf5,
    save_social_venues_to_hdf5,
    save_households_to_hdf5,
    restore_population_properties_from_hdf5,
    restore_households_properties_from_hdf5,
    restore_care_homes_properties_from_hdf5,
    restore_commute_properties_from_hdf5,
    restore_geography_properties_from_hdf5,
    restore_companies_properties_from_hdf5,
    restore_school_properties_from_hdf5,
    restore_social_venues_properties_from_hdf5,
    restore_universities_properties_from_hdf5,
    restore_hospital_properties_from_hdf5
)
from june.demography import Population
from june.demography.person import Activities, Person

logger = logging.getLogger(__name__)

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
    geo = Geography(world.areas, world.super_areas)
    save_geography_to_hdf5(geo, file_path)
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
    if world.commutecities is not None:
        logger.info("saving commute cities...")
        save_commute_cities_to_hdf5(world.commutecities, file_path)
    if world.commutehubs is not None:
        logger.info("saving commute hubs...")
        save_commute_hubs_to_hdf5(world.commutehubs, file_path)
    if world.universities is not None:
        logger.info("saving universities...")
        save_universities_to_hdf5(world.universities, file_path)
    social_venue_possible_specs = ["pubs", "groceries", "cinemas"]  # TODO: generalise
    social_venues_list = []
    for spec in social_venue_possible_specs:
        if hasattr(world, spec) and getattr(world, spec) is not None:
            social_venues_list.append(getattr(world, spec))
    if social_venues_list:
        logger.info(f"saving social venues...")
        save_social_venues_to_hdf5(social_venues_list, file_path)


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
        logger.info("loading companies...")
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
    if "commute_cities" in f_keys:
        logger.info("loading commute cities...")
        world.commutecities, world.commutecityunits = load_commute_cities_from_hdf5(
            file_path
        )
    if "commute_hubs" in f_keys:
        logger.info("loading commute hubs...")
        world.commutehubs, world.commuteunits = load_commute_hubs_from_hdf5(file_path)
    if "households" in f_keys:
        logger.info("loading households...")
        world.households = load_households_from_hdf5(file_path, chunk_size=chunk_size)
    if "population" in f_keys:
        logger.info("loading population...")
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
        logger.info("restoring population...")
        restore_population_properties_from_hdf5(
            world=world, file_path=file_path, chunk_size=chunk_size
        )
    if "households" in f_keys:
        logger.info("restoring households...")
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
    if "commute_hubs" and "commute_cities" in f_keys:
        logger.info("restoring commute...")
        restore_commute_properties_from_hdf5(world=world, file_path=file_path)
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
