import logging
import pickle
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
from june.commute import CommuteGenerator

logger = logging.getLogger(__name__)

allowed_super_groups = ["hospitals", "companies", "cemeteries", "schools", "households"]


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

    def __getstate__(self):
        """ I am being pickled! Removes links from group to people
        to avoid circular references and to make the world pickleable.
        The state of the world is then restored, however, some temporary
        information store by distributors to area or group objects
        might be deleted (they shouldn't be there anyway..)
        """
        #original_state = self.__dict__.copy()
        for supergroup_name in allowed_super_groups:
            if hasattr(self, supergroup_name):
                supergroup = getattr(self, supergroup_name)
                supergroup.erase_people_from_groups_and_subgroups()

        for geo_superunit in ["super_areas", "areas"]:
            supergeo = getattr(self, geo_superunit)
            supergeo.erase_people_from_geographical_unit()
            for geo in supergeo:
                geo.erase_people_from_geographical_unit()
        state_dict = self.__dict__.copy()  # state to pickle
        return state_dict

    def restore_world(self):
        for person in self.people:
            for subgroup in person.subgroups:
                subgroup.append(person)
            if person.area is not None:
                person.area.add(person)

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.restore_world()

    @classmethod
    def from_pickle(self, pickle_path):
        with open(pickle_path, "rb") as f:
            world = pickle.load(f)
        return world

    def to_pickle(self, save_path):
        with open(save_path, "wb") as f:
            pickle.dump(self, f)
        self.restore_world()
