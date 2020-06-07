import logging
import pickle
import h5py
from tqdm import tqdm
import numpy as np
from typing import Optional
from june.groups import Group
from june.box.box_mode import Boxes, Box
from june.demography import Demography, Population
from june.demography.person import Activities
from june.hdf5_savers import *
from june.distributors import (
    SchoolDistributor,
    HospitalDistributor,
    HouseholdDistributor,
    CareHomeDistributor,
    WorkerDistributor,
    CompanyDistributor,
)
from june.demography.geography import Geography, Areas
from june.groups import *
from june.commute import CommuteGenerator

logger = logging.getLogger(__name__)

possible_groups = ["schools", "hospitals", "companies", "care_homes"]


def _populate_areas(areas: Areas, demography):
    people = Population()
    for area in areas:
        area.populate(demography)
        people.extend(area.people)
    return people


class World:
    """
    This Class creates the world that will later be simulated.
    The world will be stored in pickle, but a better option needs to be found.
    
    Note: BoxMode = Demography +- Sociology - Geography
    """

    def __init__(self):
        """
        Initializes a world given a geography and a demography. For now, households are
        a special group because they require a mix of both groups (we need to fix
        this later). 
        """
        pass

    def distribute_people(
        self, include_households=True, include_commute=False, include_rail_travel=False
    ):
        """
        Distributes people to buildings assuming default configurations.
        """

        if self.care_homes is not None:
            carehome_distr = CareHomeDistributor()
            carehome_distr.populate_care_home_in_areas(self.areas)

        if include_households:
            household_distributor = HouseholdDistributor.from_file()
            self.households = household_distributor.distribute_people_and_households_to_areas(
                self.areas
            )

        if (
            self.companies is not None
            or self.hospitals is not None
            or self.schools is not None
        ):
            worker_distr = WorkerDistributor.for_super_areas(
                self.super_areas
            )  # atm only for_geography()
            worker_distr.distribute(
                areas=self.areas, super_areas=self.super_areas, population=self.people
            )

        if self.schools is not None:
            self.distribute_kids_and_teachers_to_schools()

        if include_commute:
            self.initialise_commuting()

        if include_rail_travel:
            self.initialise_rail_travel()

        if self.hospitals is not None:
            hospital_distributor = HospitalDistributor(self.hospitals)
            hospital_distributor.distribute_medics_to_super_areas(self.super_areas)

        self.cemeteries = self.cemeteries

        # Companies last because need hospital and school workers first
        if self.companies is not None:
            self.distribute_workers_to_companies()

    def distribute_kids_and_teachers_to_schools(self):
        school_distributor = SchoolDistributor(self.schools)
        school_distributor.distribute_kids_to_school(self.areas)
        school_distributor.distribute_teachers_to_schools_in_super_areas(
            self.super_areas
        )

    def distribute_workers_to_companies(self):
        company_distributor = CompanyDistributor()
        company_distributor.distribute_adults_to_companies_in_super_areas(
            self.super_areas
        )

    def initialise_commuting(self):
        commute_generator = CommuteGenerator.from_file()

        for area in self.areas:
            commute_gen = commute_generator.regional_gen_from_msoarea(area.name)
            for person in area.people:
                person.mode_of_transport = commute_gen.weighted_random_choice()

        # CommuteCity
        self.commutecities = CommuteCities()
        self.commutecities.from_file()
        self.commutecities.init_non_london()
        # Crucial that London is initialise second, after non-London
        self.commutecities.init_london()

        self.commutecity_distributor = CommuteCityDistributor(
            self.commutecities.members, self.super_areas.members
        )
        self.commutecity_distributor.distribute_people()

        # CommuteHub
        self.commutehubs = CommuteHubs(self.commutecities)
        self.commutehubs.from_file()
        self.commutehubs.init_hubs()

        self.commutehub_distributor = CommuteHubDistributor(self.commutecities.members)
        self.commutehub_distributor.from_file()
        self.commutehub_distributor.distribute_people()

        # CommuteUnit
        self.commuteunits = CommuteUnits(self.commutehubs.members)
        self.commuteunits.init_units()

        # CommuteCityUnit
        self.commutecityunits = CommuteCityUnits(self.commutecities.members)
        self.commutecityunits.init_units()

    def initialise_rail_travel(self):

        # TravelCity
        self.travelcities = TravelCities(self.commutecities)
        self.init_cities()

        # TravelCityDistributor
        self.travelcity_distributor = TravelCityDistributor(
            self.travelcities.members, self.super_areas.members
        )
        self.travelcity_distributor.distribute_msoas()

        # TravelUnit
        self.travelunits = TravelUnits()

    def to_hdf5(self, file_path: str, chunk_size=100000):
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
        # empty file
        with h5py.File(file_path, "w"):
            pass
        geo = Geography(self.areas, self.super_areas)
        save_geography_to_hdf5(geo, file_path)
        save_population_to_hdf5(self.people, file_path, chunk_size)
        if hasattr(self, "hospitals"):
            save_hospitals_to_hdf5(self.hospitals, file_path, chunk_size)
        if hasattr(self, "schools"):
            save_schools_to_hdf5(self.schools, file_path, chunk_size)
        if hasattr(self, "companies"):
            save_companies_to_hdf5(self.companies, file_path, chunk_size)
        if hasattr(self, "households"):
            save_households_to_hdf5(self.households, file_path, chunk_size)
        if hasattr(self, "care_homes"):
            save_care_homes_to_hdf5(self.care_homes, file_path, chunk_size)


def generate_world_from_geography(
    geography: Geography,
    demography: Optional[Demography] = None,
    box_mode=False,
    include_households=True,
    include_commute=False,
    include_rail_travel=False,
):
    """
        Initializes the world given a geometry. The demography is calculated
        with the default settings for that geography.
        """
    world = World()
    if demography is None:
        demography = Demography.for_geography(geography)
    if include_rail_travel and not include_commute:
        raise ValueError("Rail travel depends on commute and so both must be true")
    if box_mode:
        world.hospitals = Hospitals.for_box_mode()
        world.people = _populate_areas(geography, demography)
        world.boxes = Boxes([Box()])
        world.boxes.members[0].set_population(world.people)
        return world
    world.areas = geography.areas
    world.super_areas = geography.super_areas
    world.people = _populate_areas(world.areas, demography)
    for possible_group in possible_groups:
        geography_group = getattr(geography, possible_group)
        if geography_group is not None:
            setattr(world, possible_group, geography_group)
    world.distribute_people(
        include_households=include_households,
        include_commute=include_commute,
        include_rail_travel=include_rail_travel,
    )
    return world


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
    geography = load_geography_from_hdf5(file_path, chunk_size)
    world = World()
    world.areas = geography.areas
    world.super_areas = geography.super_areas
    super_areas_first_id = world.super_areas[
        0
    ].id  # in case some super areas were created before
    with h5py.File(file_path, "r") as f:
        f_keys = list(f.keys()).copy()
    if "population" in f_keys:
        world.people = load_population_from_hdf5(file_path, chunk_size)
    if "hospitals" in f_keys:
        world.hospitals = load_hospitals_from_hdf5(file_path, chunk_size)
    if "schools" in f_keys:
        world.schools = load_schools_from_hdf5(file_path, chunk_size)
    if "companies" in f_keys:
        world.companies = load_companies_from_hdf5(file_path, chunk_size)
        # first_idx = super_area_ids.index(world.companies[0].super_area, 0)
        for company in world.companies:
            # idx = np.searchsorted(super_area_ids, company.super_area)
            company.super_area = world.super_areas[
                company.super_area - super_areas_first_id
            ]
    if "care_homes" in f_keys:
        world.care_homes = load_care_homes_from_hdf5(file_path, chunk_size)
    if "households" in f_keys:
        world.households = load_households_from_hdf5(file_path, chunk_size)

    spec_mapper = {
        "hospital": "hospitals",
        "company": "companies",
        "school": "schools",
        "household": "households",
        "care_home": "care_homes",
    }
    # restore areas -> super_areas
    for area in world.areas:
        super_area_id = area.super_area
        area.super_area = world.super_areas[super_area_id - super_areas_first_id]
        area.super_area.areas.append(area)

    activities = Activities.__fields__

    # restore person -> subgroups
    first_area_id = world.areas[0].id
    pbar = tqdm(total=len(world.people))
    for person in world.people:
        pbar.update(1)
        # add to geography
        person.area = world.areas[person.area - first_area_id]
        person.area.people.append(person)
        subgroups_instances = Activities(None, None, None, None, None, None, None)
        for i, subgroup_info in enumerate(person.subgroups):
            spec, group_id, subgroup_type = subgroup_info
            if spec is None:
                continue
            supergroup = getattr(world, spec_mapper[spec])
            first_group_id = supergroup.members[0].id
            group = supergroup.members[group_id - first_group_id]
            assert group_id == group.id
            subgroup = group[subgroup_type]
            setattr(subgroups_instances, activities[i], subgroup)
        person.subgroups = subgroups_instances

    # add people in super areas
    for super_area in world.super_areas:
        for area in super_area.areas:
            super_area.people.extend(area.people)
    return world
