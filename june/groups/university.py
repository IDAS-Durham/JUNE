import numpy as np
import pandas as pd
from random import randint
from typing import List
import logging

from june.groups import Group, Subgroup, Supergroup
from june.geography import SuperAreas, Areas, Geography
from june.paths import data_path

age_to_years = {19: 1, 20: 2, 21: 3, 22: 4, 23: 5}

default_universities_filename = data_path / "input/universities/uk_universities.csv"

logger = logging.getLogger("universities")


class University(Group):
    def __init__(
        self, n_students_max=None, n_years=5, ukprn=None, area=None, coordinates = None
    ):
        self.n_students_max = n_students_max
        self.n_years = n_years
        self.ukprn = ukprn
        self.area = area
        self.coordinates = coordinates
        super().__init__()
        self.subgroups = [Subgroup(self, i) for i in range(self.n_years + 1)]

    @property
    def students(self):
        return [person for subgroup in self.subgroups for person in subgroup]

    @property
    def n_students(self):
        return sum([subgroup.size for subgroup in self.subgroups])

    @property
    def professors(self):
        return self.subgroups[0].people

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
            self.subgroups[0].append(person)
            person.subgroups.primary_activity = self.subgroups[0]

    @property
    def is_full(self):
        return self.n_students >= self.n_students_max


class Universities(Supergroup):
    def __init__(self, universities: List[University]):
        super().__init__(members=universities)

    @classmethod
    def for_areas(
        cls,
        areas: Areas,
        universities_filename: str = default_universities_filename,
        max_distance_to_area=5,
    ):
        """
        Initializes universities from super areas. By looking at the coordinates
        of each university in the filename, we initialize those universities who
        are close to any of the super areas.

        Parameters
        ----------
        areas:
            an instance of Areas
        universities_filename:
            path to the university data
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
            university = University(
                area=closest_area, n_students_max=n_stud, ukprn=ukprn, coordinates=coord
            )
            universities.append(university)
        logger.info(f"There are {len(universities)} universities in this world.")
        return cls(universities)

    @classmethod
    def for_geography(
        cls,
        geography: Geography,
        universities_filename: str = default_universities_filename,
        max_distance_to_area: float = 20,
    ):
        return cls.for_areas(
            geography.areas,
            universities_filename=universities_filename,
            max_distance_to_area=max_distance_to_area,
        )
