import logging
import random
import pandas as pd
from typing import Optional
from june.demography import Demography, Population
from june.distributors import (
    SchoolDistributor,
    HospitalDistributor,
    HouseholdDistributor,
    CareHomeDistributor,
    WorkerDistributor,
    CompanyDistributor,
    UniversityDistributor,
)
from june.distributors.friendship_distributor import FriendshipDistributor
from june.distributors.sexual_relationship_distributor import SexualRelationshipDistributor
from june.epidemiology.infection.disease_config import DiseaseConfig
from june.geography import Geography, Areas, Airport, Airports
from june.groups import Supergroup, Cemeteries

logger = logging.getLogger("world")

possible_groups = [
    "households",
    "care_homes",
    "schools",
    "hospitals",
    "companies",
    "universities",
    "airports",
    "pubs",
    "groceries",
    "cinemas",
]


def _populate_areas(areas: Areas, demography, ethnicity=True, comorbidity=True):
    logger.info("Populating areas")
    people = Population()
    for area in areas:
        area.populate(demography, ethnicity=ethnicity, comorbidity=comorbidity)
        people.extend(area.people)
    n_people = len(people)
    logger.info(f"Areas populated. This world's population is: {n_people}")

    # Visualization of the final product
    print("\n===== Sample of Combined Population Across Areas =====")
    sample_population = [{
        "| Person ID": person.id,
        "| Area": person.area.name if hasattr(person, "area") else "Unknown",
        "| Age": person.age,
        "| Sex": person.sex,
        "| Ethnicity": person.ethnicity,
        "| Comorbidity": getattr(person, 'comorbidity', None),
        "| Hobbies": ", ".join(person.hobbies) if hasattr(person, "hobbies") and person.hobbies else "None"
    } for person in random.sample(people.people, min(10, n_people))]

    df_population = pd.DataFrame(sample_population)
    print(df_population)
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
        from june.mpi_wrapper import MovablePeople
        
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
        self.airports = None
        self.aircrafts = None
        self.cities = None
        self.stations = None
        self.friendships = None  # Add a FriendshipDistributor attribute
        self.movable_people = MovablePeople()  # Initialize MovablePeople


    def __iter__(self):
        ret = []
        for attr_name, attr_value in self.__dict__.items():
            if isinstance(attr_value, Supergroup):
                ret.append(attr_value)
        return iter(ret)

    def distribute_people(self, include_households=True):
        """
        Distributes people to buildings, using configurations and settings.

        Parameters
        ----------
        include_households : bool, default=True
            Whether to include household distribution.
        disease_config : DiseaseConfig, optional
            Disease-specific configurations.
        """
        try:
            # Distribute workers if any relevant groups exist
            if (
                self.companies is not None
                or self.hospitals is not None
                or self.schools is not None
                or self.care_homes is not None
            ):
                try:
                    worker_distr = WorkerDistributor.for_super_areas(
                        area_names=[super_area.name for super_area in self.super_areas],
                    )
                    worker_distr.distribute(
                        areas=self.areas, super_areas=self.super_areas, population=self.people
                    )
                except Exception as e:
                    logger.warning(f"Error during worker distribution: {e}")

            # Handle care homes
            if self.care_homes is not None:
                try:
                    carehome_distr = CareHomeDistributor.from_file()
                    carehome_distr.populate_care_homes_in_super_areas(
                        super_areas=self.super_areas
                    )
                except Exception as e:
                    logger.warning(f"Error populating care homes: {e}")

            # Handle households
            if include_households:
                try:
                    household_distributor = HouseholdDistributor.from_file()
                    self.households = household_distributor.distribute_people_and_households_to_areas(
                        self.areas
                    )
                except Exception as e:
                    logger.warning(f"Error distributing households: {e}")
                    # Ensure households is not None even if distribution fails
                    if self.households is None:
                        self.households = []

            # Handle schools
            if self.schools is not None:
                try:
                    school_distributor = SchoolDistributor(self.schools)
                    school_distributor.distribute_kids_to_school(self.areas)
                    school_distributor.limit_classroom_sizes()
                    school_distributor.distribute_teachers_to_schools_in_super_areas(
                        self.super_areas
                    )
                except Exception as e:
                    logger.warning(f"Error distributing schools: {e}")

            # Handle universities
            if self.universities is not None:
                try:
                    uni_distributor = UniversityDistributor(self.universities)
                    uni_distributor.distribute_students_to_universities(
                        areas=self.areas, people=self.people
                    )
                except Exception as e:
                    logger.warning(f"Error distributing universities: {e}")

            # Distribute care home workers
            if self.care_homes is not None:
                try:
                    carehome_distr.distribute_workers_to_care_homes(
                        super_areas=self.super_areas
                    )
                except Exception as e:
                    logger.warning(f"Error distributing care home workers: {e}")

            # Handle hospitals
            if self.hospitals is not None:
                try:
                    hospital_distributor = HospitalDistributor.from_file(
                        self.hospitals
                    )
                    hospital_distributor.distribute_medics_to_super_areas(
                        self.super_areas
                    )
                    hospital_distributor.assign_closest_hospitals_to_super_areas(
                        self.super_areas
                    )
                except Exception as e:
                    logger.warning(f"Error distributing hospitals: {e}")

            # Handle companies
            if self.companies is not None:
                try:
                    company_distributor = CompanyDistributor()
                    company_distributor.distribute_adults_to_companies_in_super_areas(
                        self.super_areas
                    )
                except Exception as e:
                    logger.warning(f"Error distributing companies: {e}")
            
            # Handle friendships and relationships
            if self.people and len(self.people.people) > 0:
                try:
                    friendship_distributor = FriendshipDistributor(
                        people=self.people.people)
                    """ sexual_relationship_distributor = SexualRelationshipDistributor(
                        people=self.people.people,
                        random_seed=12345  # Use a fixed seed for reproducibility
                        ) """
                    
                    friendship_distributor.link_all_friends(
                        super_areas=self.super_areas,
                    )

                    #sexual_relationship_distributor.distribute_sexual_relationships(super_areas=self.super_areas)
                except Exception as e:
                    logger.warning(f"Error distributing friendships or relationships: {e}")
        except Exception as e:
            logger.error(f"An error occurred during people distribution: {e}")
            # Ensure the world can still be created even if distribution fails


            
        

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
    Initializes the world given a geography. The demography is calculated
    with the default settings for that geography.

    Parameters
    ----------
    geography : Geography
        The geographical data.
    demography : Demography, optional
        Demography data for the geography.
    include_households : bool, default=True
        Whether to include households in the world.
    ethnicity : bool, default=True
        Whether to include ethnicity data.
    comorbidity : bool, default=True
        Whether to include comorbidity data.
    """
    from june.groups.travel import Aircrafts

    world = World()
    if demography is None:
        demography = Demography.for_geography(geography)
    world.areas = geography.areas
    world.super_areas = geography.super_areas
    world.regions = geography.regions
    world.people = _populate_areas(world.areas, demography)
    
    # Add transfer of airports and aircraft with proper checks
    if hasattr(geography, 'airports') and geography.airports is not None:
        world.airports = geography.airports
        # Initialize aircraft fleet based on airports
        world.aircrafts = Aircrafts.from_airports(world.airports)
        logger.info(f"Added {len(geography.airports)} airports to world")
        logger.info(f"Created aircraft fleet with {len(world.aircrafts)} aircraft")
    else:
        logger.info("No airports found in geography")
        world.airports = None
        world.aircrafts = None
    
    # Transfer groups from geography to world
    for possible_group in possible_groups:
        try:
            geography_group = getattr(geography, possible_group)
            if geography_group is not None:
                setattr(world, possible_group, geography_group)
            else:
                logger.info(f"No {possible_group} found in geography yet. This component will be skipped for now.")
        except AttributeError:
            logger.info(f"No {possible_group} attribute found in geography. This component will be skipped.")
    
    # Distribute people based on available groups
    world.distribute_people(
        include_households=include_households
    )

    world.cemeteries = Cemeteries()
    return world
