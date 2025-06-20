import numpy as np
import pandas as pd
import random
from random import randint
from typing import List, Tuple
import logging

from june.epidemiology.infection.disease_config import DiseaseConfig
from june.geography.geography import Area
from june.groups import Group, Subgroup, Supergroup
from june.geography import Areas, Geography
from june.paths import data_path

age_to_years = {19: 0, 20: 1, 21: 2, 22: 3, 23: 4}

default_universities_filename = data_path / "input/universities/uk_universities.csv"

logger = logging.getLogger("universities")


class University(Group):
    def __init__(
        self,
        n_students_max: int = None,
        n_years: int = 5,
        ukprn: str = None,
        area: Area = None,
        coordinates: Tuple[float, float] = None,
        registered_members_ids: dict = None
    ):
        """
        Create a University given its description.

        Parameters
        ----------
        n_students_max : int
            Maximum number of students that can attend the university.
        n_years : int
            Number of academic years in the university.
        ukprn : str
            Unique identifier for the university.
        area : Area
            The area the university belongs to.
        coordinates : Tuple[float, float]
            Latitude and longitude of the university.
        registered_members_ids : dict, optional
            A dict mapping subgroup IDs to lists of member IDs.
        """
        super().__init__()
        self.n_students_max = n_students_max
        self.n_years = n_years
        self.ukprn = ukprn
        self.area = area
        self.coordinates = coordinates
        self.subgroups = [Subgroup(self, i) for i in range(self.n_years)]
        self.registered_members_ids = registered_members_ids if registered_members_ids is not None else {}

    @property
    def students(self):
        return [person for subgroup in self.subgroups[:] for person in subgroup]

    @property
    def n_students(self):
        return sum([self.subgroups[i].size for i in range(1, len(self.subgroups))])

    @property
    def super_area(self):
        return self.area.super_area

    def add(self, person, subgroup="student"):
        if subgroup == "student":
            if person.age not in age_to_years:
                year = randint(0, len(self.subgroups) - 1)
            else:
                year = age_to_years[person.age]
            self.subgroups[year].append(person)
            person.subgroups.primary_activity = self.subgroups[year]
            if person.work_super_area is not None:
                person.work_super_area.remove_worker(person)
        elif subgroup == "professors":
            # No professors in the modeling of the code!
            self.subgroups[0].append(person)
            person.subgroups.primary_activity = self.subgroups[0]
            
    def add_to_registered_members(self, person_id, subgroup_type=0):
        """
        Add a person to the registered members list for a specific subgroup.
        
        Parameters
        ----------
        person_id : int
            The ID of the person to add
        subgroup_type : int, optional
            The subgroup to add the person to (default: 0)
        """
        # Create the subgroup if it doesn't exist
        if subgroup_type not in self.registered_members_ids:
            self.registered_members_ids[subgroup_type] = []
            
        # Add the person if not already in the list
        if person_id not in self.registered_members_ids[subgroup_type]:
            self.registered_members_ids[subgroup_type].append(person_id)

    @property
    def is_full(self):
        return self.n_students >= self.n_students_max


class Universities(Supergroup):
    venue_class = University

    def __init__(self, universities: List[venue_class]):
        super().__init__(members=universities)

    @classmethod
    def for_areas(
        cls,
        areas: Areas,
        universities_filename: str,
        max_distance_to_area: float,
    ) -> "Universities":
        """
        Initializes universities based on proximity to areas.

        Parameters
        ----------
        areas : Areas
            Areas where universities will be created.
        universities_filename : str
            Path to the university data file.
        max_distance_to_area : float
            Maximum allowable distance to assign a university to an area.
        disease_config : DiseaseConfig
            The disease configuration object containing relevant settings.

        Returns
        -------
        Universities
            An instance containing all created universities.
        """
        universities_df = pd.read_csv(universities_filename)
        longitudes = universities_df["longitude"].values
        latitudes = universities_df["latitude"].values
        coordinates = np.array(list(zip(latitudes, longitudes)))
        n_students = universities_df["n_students"].values
        ukprn_values = universities_df["UKPRN"].values

        universities = []
        for coord, n_stud, ukprn in zip(coordinates, n_students, ukprn_values):
            closest_area, distance = areas.get_closest_areas(
                coordinates=coord, return_distance=True, k=1
            )
            distance = distance[0]
            closest_area = closest_area[0]
            if distance > max_distance_to_area:
                continue
            university = cls.venue_class(
                area=closest_area,
                n_students_max=n_stud,
                ukprn=ukprn,
                coordinates=coord,
            )
            universities.append(university)

        logger.info(f"There are {len(universities)} universities in this world.")

        # Visualization - Sample 5 universities for inspection
        sample_universities = [
            {
                "| Uni ID": uni.id,
                "| Area": uni.area.name if uni.area else "Unknown",
                "| UKPRN": uni.ukprn,
                "| Max Students": uni.n_students_max,
                "| Coordinates": uni.coordinates,
            }
            for uni in random.sample(universities, min(5, len(universities)))
        ]

        df_universities = pd.DataFrame(sample_universities)
        print("\n===== Sample of Created Universities =====")
        print(df_universities)

        return cls(universities)

    @classmethod
    def for_geography(
        cls,
        geography: Geography,
        universities_filename: str = default_universities_filename,
        max_distance_to_area: float = 20,
    ) -> "Universities":
        """
        Create universities for a given geography.

        Parameters
        ----------
        geography : Geography
            The geography object with areas to initialize universities.
        disease_config : DiseaseConfig
            The disease configuration object containing relevant settings.
        max_distance_to_area : float
            Maximum distance from an area to consider a university.

        Returns
        -------
        Universities
            An instance containing all created universities.
        """
        return cls.for_areas(
            geography.areas,
            universities_filename=universities_filename,
            max_distance_to_area=max_distance_to_area,
        )

    # @property
    # def n_professors(self):
    #     return sum([uni.n_professors for uni in self.members])

    @property
    def n_students(self):
        return sum([uni.n_students for uni in self.members])
