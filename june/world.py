import logging
import pickle

from june.box.box_mode import Boxes, Box
from june.demography import Demography, Population
from june.distributors import (
    SchoolDistributor,
    HospitalDistributor,
    HouseholdDistributor,
    CareHomeDistributor,
    WorkerDistributor,
    CompanyDistributor,
)
from june.geography import Geography
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
        demography: Demography,
        include_households: bool = True,
        include_commute: bool = False,
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
        self.people = _populate_areas(geography, demography)

        if hasattr(geography, "care_homes"):
            self.care_homes = geography.care_homes
            self.distribute_people_to_care_homes()
        if include_households:
            self.distribute_people_to_households()
        if (
            hasattr(geography, "companies")
            or hasattr(geography, "hospitals")
            or hasattr(geography, "schools")
        ):
            self.distribute_workers_to_super_areas(geography)

        if hasattr(geography, "schools"):
            self.schools = geography.schools
            self.distribute_kids_and_teachers_to_schools()

        if hasattr(geography, "companies"):
            self.companies = geography.companies
            self.distribute_workers_to_companies()

        if include_commute:
            self.initialise_commuting()

        if hasattr(geography, "hospitals"):
            self.hospitals = geography.hospitals
            self.distribute_medics_to_hospitals()

        if hasattr(geography, "cemeteries"):
            self.cemeteries = geography.cemeteries

    @classmethod
    def from_geography(cls, geography: Geography, box_mode=False):
        """
        Initializes the world given a geometry. The demography is calculated
        with the default settings for that geography.
        """
        demography = Demography.for_geography(geography)
        return cls(geography, demography, box_mode=box_mode)

    def to_pickle(self, save_path):
        with open(save_path, "wb") as f:
            pickle.dump(self, f)

    def distribute_people_to_households(self):
        household_distributor = HouseholdDistributor.from_file()
        self.households = household_distributor.distribute_people_and_households_to_areas(
            self.areas
        )

    def distribute_people_to_care_homes(self):
        CareHomeDistributor().populate_care_home_in_areas(self.areas)

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

        # put these into the simulator
        # self.commuteunit_distributor = CommuteUnitDistributor(self.commutehubs.members)

        # CommuteCityUnit
        self.commutecityunits = CommuteCityUnits(self.commutecities.members)
        self.commutecityunits.init_units()

        # put these into the simulator
        # self.commutecityunit_distributor = CommuteCityUnitDistributor(self.commutecities.members)

