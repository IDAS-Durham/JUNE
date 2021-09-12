import logging
import h5py
from collections import defaultdict
from tqdm import tqdm
import numpy as np
from typing import Optional
from june.demography import Demography, Population
from june.demography.person import Activities, Person
from june.distributors import (
    SchoolDistributor,
    HospitalDistributor,
    HouseholdDistributor,
    CareHomeDistributor,
    WorkerDistributor,
    CompanyDistributor,
    UniversityDistributor,
)
from june.geography import Geography, Areas
from june.groups import Supergroup, Hospitals, Cemeteries

logger = logging.getLogger("world")

possible_groups = [
    "households",
    "care_homes",
    "schools",
    "hospitals",
    "companies",
    "universities",
    "pubs",
    "groceries",
    "cinemas",
]


def _populate_areas(
    areas: Areas, demography, ethnicity=True, comorbidity=True
):
    logger.info(f"Populating areas")
    people = Population()
    for area in areas:
        area.populate(
            demography,
            ethnicity=ethnicity,
            comorbidity=comorbidity,
        )
        people.extend(area.people)
    n_people = len(people)
    logger.info(f"Areas populated. This world's population is: {n_people}")
    return people


class World:
    """
    This Class creates the world that will later be simulated.
    The world will be stored in pickle, but a better option needs to be found.
    
    """

    def __init__(self):
        """
        Initializes a world given a geography and a demography. For now, households are
        a special group because they require a mix of both groups (we need to fix
        this later). 
        """
        self.areas = None
        self.super_areas = None
        self.regions = None
        self.people = None
        self.households = None
        self.care_homes = None
        self.schools = None
        self.companies = None
        self.hospitals = None
        self.pubs = None
        self.groceries = None
        self.cinemas = None
        self.cemeteries = None
        self.universities = None
        self.cities = None
        self.stations = None

    def __iter__(self):
        ret = []
        for attr_name, attr_value in self.__dict__.items():
            if isinstance(attr_value, Supergroup):
                ret.append(attr_value)
        return iter(ret)


    def distribute_people(self, include_households=True):
        """
        Distributes people to buildings assuming default configurations.
        """
        if (
            self.companies is not None
            or self.hospitals is not None
            or self.schools is not None
            or self.care_homes is not None
        ):
            worker_distr = WorkerDistributor.for_super_areas(
                area_names=[super_area.name for super_area in self.super_areas]
            )  # atm only for_geography()
            worker_distr.distribute(
                areas=self.areas, super_areas=self.super_areas, population=self.people
            )
        if self.care_homes is not None:
            carehome_distr = CareHomeDistributor.from_file()
            carehome_distr.populate_care_homes_in_super_areas(
                super_areas=self.super_areas
            )

        if include_households:
            household_distributor = HouseholdDistributor.from_file()
            self.households = household_distributor.distribute_people_and_households_to_areas(
                self.areas
            )

        if self.schools is not None:
            school_distributor = SchoolDistributor(self.schools)
            school_distributor.distribute_kids_to_school(self.areas)
            school_distributor.limit_classroom_sizes()
            school_distributor.distribute_teachers_to_schools_in_super_areas(
                self.super_areas
            )

        if self.universities is not None:
            uni_distributor = UniversityDistributor(self.universities)
            uni_distributor.distribute_students_to_universities(
                areas=self.areas, people=self.people
            )
        if self.care_homes is not None:
            # this goes after unis to ensure students go to uni
            carehome_distr.distribute_workers_to_care_homes(
                super_areas=self.super_areas
            )

        if self.hospitals is not None:
            hospital_distributor = HospitalDistributor.from_file(self.hospitals)
            hospital_distributor.distribute_medics_to_super_areas(self.super_areas)
            hospital_distributor.assign_closest_hospitals_to_super_areas(
                self.super_areas
            )

        # Companies last because need hospital and school workers first
        if self.companies is not None:
            company_distributor = CompanyDistributor()
            company_distributor.distribute_adults_to_companies_in_super_areas(
                self.super_areas
            )

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
        from june.hdf5_savers import save_world_to_hdf5

        save_world_to_hdf5(world=self, file_path=file_path, chunk_size=chunk_size)


def generate_world_from_geography(
    geography: Geography,
    demography: Optional[Demography] = None,
    include_households=True,
    ethnicity=True,
    comorbidity=True,
):
    """
    Initializes the world given a geometry. The demography is calculated
    with the default settings for that geography.
    """
    world = World()
    if demography is None:
        demography = Demography.for_geography(geography)
    world.areas = geography.areas
    world.super_areas = geography.super_areas
    world.regions = geography.regions
    world.people = _populate_areas(world.areas, demography)
    for possible_group in possible_groups:
        geography_group = getattr(geography, possible_group)
        if geography_group is not None:
            setattr(world, possible_group, geography_group)
    world.distribute_people(include_households=include_households,)
    world.cemeteries = Cemeteries()
    return world
