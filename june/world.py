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
from june.demography.geography import Geography
from june.groups import *
from june.commute import CommuteGenerator

logger = logging.getLogger(__name__)


def _populate_areas(geography, demography):
    people = Population()
    for area in geography.areas:
        area.populate(demography)
        people.extend(area.people)
    return people


class World:
    """
    This Class creates the world that will later be simulated.
    The world will be stored in pickle, but a better option needs to be found.
    
    Note: BoxMode = Demography +- Sociology - Geography
    """

    def __init__(
        self,
        geography: Geography,
        demography: Optional[Demography] = None,
        include_households: bool = True,
        include_commute: bool = False,
        include_rail_travel: bool = False,
        box_mode=False,
    ):
        """
        Initializes a world given a geography and a demography. For now, households are
        a special group because they require a mix of both groups (we need to fix
        this later). 

        Parameters
        ----------
        geography
            an instance of the Geography class specifying the "board"
        demography
            an instance of the Demography class with generators to generate people with 
            certain demographic attributes
        include_households
            whether to include households in the world or not (defualt = True)
        """
        if include_rail_travel and not include_commute:
            raise ValueError("Rail travel depends on commute and so both must be true")

        self.box_mode = box_mode
        if self.box_mode:
            self.hospitals = Hospitals.for_box_mode()
            self.people = _populate_areas(geography, demography)
            self.boxes = Boxes([Box()])
            self.boxes.members[0].set_population(self.people)
            return
        self.areas = geography.areas
        self.super_areas = geography.super_areas
        print("populating the world's geography with the specified demography...")
        if demography is not None:
            self.people = _populate_areas(geography, demography)

        if (
            geography.companies is not None
            or geography.hospitals is not None
            or geography.schools is not None
            or geography.care_homes is not None
        ):
            self.distribute_workers_to_super_areas(geography)

        if geography.care_homes is not None:
            self.care_homes = geography.care_homes
            self.distribute_people_to_care_homes()

        if include_households:
            self.distribute_people_to_households()

        if geography.schools is not None:
            self.schools = geography.schools
            self.distribute_kids_and_teachers_to_schools()

        if include_commute:
            self.initialise_commuting()

        if include_rail_travel:
            self.initialise_rail_travel()

        if geography.hospitals is not None:
            self.hospitals = geography.hospitals
            self.distribute_medics_to_hospitals()

        if geography.cemeteries is not None:
            self.cemeteries = geography.cemeteries

        # Companies last because need hospital and school workers first
        if geography.companies is not None:
            self.companies = geography.companies
            self.distribute_workers_to_companies()

    @classmethod
    def from_geography(
        cls, geography: Geography, box_mode=False, include_households=True
    ):
        """
        Initializes the world given a geometry. The demography is calculated
        with the default settings for that geography.
        """
        demography = Demography.for_geography(geography)
        return cls(
            geography,
            demography,
            box_mode=box_mode,
            include_households=include_households,
        )

    def distribute_people_to_households(self):
        household_distributor = HouseholdDistributor.from_file()
        self.households = household_distributor.distribute_people_and_households_to_areas(
            self.areas
        )

    def distribute_people_to_care_homes(self):
        carehome_distr = CareHomeDistributor()
        carehome_distr.populate_care_home_in_areas(self.areas)

    def distribute_workers_to_super_areas(self, geography):
        worker_distr = WorkerDistributor.for_geography(
            geography
        )  # atm only for_geography()
        worker_distr.distribute(geography, self.people)

    def distribute_medics_to_hospitals(self):
        hospital_distributor = HospitalDistributor(self.hospitals)
        hospital_distributor.distribute_medics_to_super_areas(self.super_areas)

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
        if hasattr(self, "commutecities"):
            save_commute_cities_to_hdf5(self.commutecities, file_path)
        if hasattr(self, "commutehubs"):
            save_commute_hubs_to_hdf5(self.commutehubs, file_path)


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
    world = World(geography, include_households=False)
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
        for company in world.companies:
            company.super_area = world.super_areas[
                company.super_area - super_areas_first_id
            ]
    if "care_homes" in f_keys:
        world.care_homes = load_care_homes_from_hdf5(file_path, chunk_size)
    if "households" in f_keys:
        world.households = load_households_from_hdf5(file_path, chunk_size)
    if "commute_cities" in f_keys:
        world.commutecities = load_commute_cities_from_hdf5(file_path)
        world.commutecityunits = CommuteCityUnits(world.commutecities.members)
    if "commute_hubs" in f_keys:
        world.commutehubs = load_commute_hubs_from_hdf5(file_path)
        world.commuteunits = CommuteUnits(world.commutehubs.members)

    spec_mapper = {
        "hospital": "hospitals",
        "company": "companies",
        "school": "schools",
        "household": "households",
        "care_home": "care_homes",
        "commute_hub" : "commutehubs",
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

    # commute
    if hasattr(world, "commutehubs") and hasattr(world, "commutecities"):
        first_hub_idx = world.commutehubs[0].id
        first_person_idx = world.people[0].id
        for city in world.commutecities:
            city.commutehubs = list(city.commutehubs)
            for i in range(0, len(city.commutehubs)):
                city.commutehubs[i] = world.commutehubs[
                    city.commutehubs[i] - first_hub_idx
                ]

            commute_internal_people = []
            for i in range(0, len(city.commute_internal)):
                commute_internal_people.append(
                    world.people[city.commute_internal[i] - first_person_idx]
                )
            city.commute_internal = commute_internal_people
        for hub in world.commutehubs:
            hub_people_ids = [person_id for person_id in hub.people]
            hub.clear()
            for person_id in hub_people_ids:
                hub.add(world.people[person_id - first_person_idx])

    return world
