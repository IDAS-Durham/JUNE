import logging
import pickle
import h5py
from june.groups import Group
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

logger = logging.getLogger(__name__)

allowed_super_groups = [
    "hospitals",
    "companies",
    "cemeteries",
    "schools",
    "households",
    "care_homes",
]


def _populate_areas(geography, demography):
    people = Population()
    for area in geography.areas:
        area.populate(demography)
        people.extend(area.people)
    return people


class World(object):
    """
    This Class creates the world that will later be simulated.
    The world will be stored in pickle, but a better option needs to be found.
    
    Note: BoxMode = Demography +- Sociology - Geography
    """

    def __init__(
        self,
        geography: Geography,
        demography: Demography = None,
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
        if demography is not None:
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

        if include_commute:
            self.initialise_commuting()

        if hasattr(geography, "hospitals"):
            self.hospitals = geography.hospitals
            self.distribute_medics_to_hospitals()

        if hasattr(geography, "cemeteries"):
            self.cemeteries = geography.cemeteries

        # Companies last because need hospital and school workers first
        if hasattr(geography, "companies"):
            self.companies = geography.companies
            self.distribute_workers_to_companies()

    @classmethod
    def from_geography(cls, geography: Geography, box_mode=False):
        """
        Initializes the world given a geometry. The demography is calculated
        with the default settings for that geography.
        """
        demography = Demography.for_geography(geography)
        return cls(geography, demography, box_mode=box_mode)

    def _destroy_world(self):
        """ I am being pickled! Removes links from group to people
        to avoid circular references and to make the world pickleable.
        The state of the world is then restored, however, some temporary
        information store by distributors to area or group objects
        might be deleted (they shouldn't be there anyway..)
        """
        for supergroup_name in allowed_super_groups:
            if hasattr(self, supergroup_name):
                supergroup = getattr(self, supergroup_name)
                supergroup.erase_people_from_groups_and_subgroups()

        for geo_superunit in ["super_areas", "areas"]:
            supergeo = getattr(self, geo_superunit)
            supergeo.erase_people_from_geographical_unit()

    def _restore_world(self):
        # restore subgroup -> group link
        for supergroup_name in allowed_super_groups:
            if hasattr(self, supergroup_name):
                supergroup = getattr(self, supergroup_name)
                for group in supergroup:
                    for subgroup in group.subgroups:
                        subgroup.group = group
        for person in self.people:
            for subgroup in person.subgroups:
                if subgroup is None:
                    continue
                subgroup.append(person)
                if isinstance(subgroup.group, Household):
                    # restore housemates
                    for mate in subgroup.group.people:
                        if mate != person:
                            person.housemates.append(mate)
                # restore subgroups.people
            # restore area.people
            if person.area is not None:
                person.area.add(person)
        # restore super_areas.areas
        for area in self.areas:
            area.super_area.areas.append(area)

    #
    def __setstate__(self, state):
        self.__dict__.update(state)
        self._restore_world()

    def __getstate__(self):
        """
        The world is being pickled. If the user calls pickle directly,
        without using the to_pickle method, then the connections from
        the groups to people will be destroyed, and the user has to call
        self._restore_world() manually. It is advised then to only use the
        to_pickle() method.
        """
        self._destroy_world()
        return self.__dict__

    @classmethod
    def from_pickle(self, pickle_path):
        with open(pickle_path, "rb") as f:
            world = pickle.load(f)
        return world

    def to_pickle(self, save_path):
        with open(save_path, "wb") as f:
            pickle.dump(self, f)
        self._restore_world()

    # @profile
    def distribute_people_to_households(self):
        household_distributor = HouseholdDistributor.from_file()
        self.households = household_distributor.distribute_people_and_households_to_areas(
            self.areas
        )

    # @profile
    def distribute_people_to_care_homes(self):
        CareHomeDistributor().populate_care_home_in_areas(self.areas)

    # @profile
    def distribute_workers_to_super_areas(self, geography):
        worker_distr = WorkerDistributor.for_geography(
            geography
        )  # atm only for_geography()
        worker_distr.distribute(geography, self.people)

    # @profile
    def distribute_medics_to_hospitals(self):
        hospital_distributor = HospitalDistributor(self.hospitals)
        hospital_distributor.distribute_medics_to_super_areas(self.super_areas)

    # @profile
    def distribute_kids_and_teachers_to_schools(self):
        school_distributor = SchoolDistributor(self.schools)
        school_distributor.distribute_kids_to_school(self.areas)
        school_distributor.distribute_teachers_to_schools_in_super_areas(
            self.super_areas
        )

    # @profile
    def distribute_workers_to_companies(self):
        company_distributor = CompanyDistributor()
        company_distributor.distribute_adults_to_companies_in_super_areas(
            self.super_areas
        )

    # @profile
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

    def to_hdf5(self, file_path: str):
        # empty file
        with h5py.File(file_path, "w"):
            pass
        supergroups_to_save = [
            "hospitals",
            "companies",
            "schools",
            "households",
            "care_homes",
        ]
        for supergroup_name in supergroups_to_save:
            if hasattr(self, supergroup_name):
                supergroup = getattr(self, supergroup_name)
                supergroup.to_hdf5(file_path)
        geo = Geography(self.areas, self.super_areas)
        self.people.to_hdf5(file_path)
        geo.to_hdf5(file_path)


def generate_world_from_hdf5(file_path: str) -> World:
    geography = Geography.from_hdf5(file_path)
    world = World(geography, include_households=False)
    with h5py.File(file_path) as f:
        f_keys = list(f.keys()).copy()
    if "population" in f_keys:
        world.people = Population.from_hdf5(file_path)
    if "hospitals" in f_keys:
        world.hospitals = Hospitals.from_hdf5(file_path)
    if "schools" in f_keys:
        world.schools = Schools.from_hdf5(file_path)
    if "companies" in f_keys:
        world.companies = Companies.from_hdf5(file_path)
        for company in world.companies:
            sa_id = company.super_area
            company.super_area = world.super_areas[sa_id]
    if "care_homes" in f_keys:
        world.care_homes = CareHomes.from_hdf5(file_path)
    if "households" in f_keys:
        world.households = Households.from_hdf5(file_path)

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
        area.super_area = world.super_areas[super_area_id]
        area.super_area.areas.append(area)

    # restore person -> subgroups
    for person in world.people:
        subgroups_instances = [None] * len(person.subgroups)
        for i, subgroup_info in enumerate(person.subgroups):
            spec, group_id, subgroup_type = subgroup_info
            if spec is None:
                continue
            supergroup = getattr(world, spec_mapper[spec])
            group = supergroup.members[group_id]
            assert group_id == group.id
            subgroup = group[subgroup_type]
            subgroups_instances[i] = subgroup
        person.subgroups = subgroups_instances
        # restore housemates
        housemate_ids = person.housemates
        housemates = []
        for mateid in housemate_ids:
            housemates.append(world.people[mateid])
        person.housemates = housemates
    return world

