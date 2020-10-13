import logging
import yaml
from enum import IntEnum
import math
from itertools import count
from copy import deepcopy
from june import paths
from typing import List, Tuple, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from june.geography import Geography, Areas, Area
from june.groups.group import Group, Subgroup, Supergroup


default_data_filename = paths.data_path / "input/schools/england_schools.csv"
default_areas_map_path = paths.data_path / "input/geography/area_super_area_region.csv"
default_config_filename = paths.configs_path / "defaults/groups/schools.yaml"

logger = logging.getLogger("schools")


class SchoolError(BaseException):
    pass


class School(Group):

    __slots__ = (
        "id",
        "coordinates",
        "n_pupils_max",
        "n_teachers_max",
        "age_min",
        "age_max",
        "age_structure",
        "sector",
        "years",
    )

    class SubgroupType(IntEnum):
        teachers = 0
        students = 1

    def __init__(
        self,
        coordinates: Tuple[float, float] = None,
        n_pupils_max: int = None,
        age_min: int = 0,
        age_max: int = 18,
        sector: str = None,
        area: Area = None,
        n_classrooms: Optional[int] = None,
        years: Optional[int] = None,
    ):
        """
        Create a School given its description.

        Parameters
        ----------
        coordinates:
            latitude and longitude 
        n_pupils_max:
            maximum number of pupils that can attend the school
        age_min:
            minimum age of the pupils
        age_max:
            maximum age of the pupils
        sector:
            whether it is a "primary", "secondary" or both "primary_secondary"
        area:
            area the school belongs to
        n_classrooms:
            number of classrooms in the school
        years:
            age group year per classroom

        number of SubGroups N = age_max-age_min year +1 (student years) + 1 (teachers):
        0 - teachers
        1 - year of lowest age (age_min)
        ...
        n - year of highest age (age_max)
        """
        super().__init__()
        self.subgroups = []
        # for i, _ in enumerate(range(age_min, age_max + 2)):
        if n_classrooms is None:
            n_classrooms = age_max - age_min
        self.subgroups = [Subgroup(self, i) for i in range(n_classrooms + 2)]
        self.n_classrooms = n_classrooms
        self.coordinates = coordinates
        self.area = area
        self.n_pupils_max = n_pupils_max
        self.n_teachers_max = None
        self.age_min = age_min
        self.age_max = age_max
        self.sector = sector
        if years is None:
            self.years = tuple(range(age_min, age_max + 1))
        else:
            self.years = tuple(years)

    def add(self, person, subgroup_type=SubgroupType.students):
        if subgroup_type == self.SubgroupType.students:
            subgroup = self.subgroups[1 + person.age - self.age_min]
            subgroup.append(person)
            person.subgroups.primary_activity = subgroup
        else:  # teacher
            subgroup = self.subgroups[self.SubgroupType.teachers]
            subgroup.append(person)
            person.subgroups.primary_activity = subgroup

    def limit_classroom_sizes(self, max_classroom_size: int):
        """
        Make all subgroups smaller than ```max_classroom_size```

        Parameters
        ----------
        max_classroom_size:
           maximum number of students per classroom (subgroup)
        """
        age_subgroups = self.subgroups.copy()
        year_age_group = deepcopy(self.years)
        self.subgroups = [age_subgroups[0]]  # keep teachers
        self.years = []
        counter = 1
        for idx, subgroup in enumerate(age_subgroups[1:]):
            if len(subgroup.people) > max_classroom_size:
                n_classrooms = math.ceil(len(subgroup.people) / max_classroom_size)
                self.years += [year_age_group[idx]] * n_classrooms
                pupils_in_classroom = np.array_split(subgroup.people, n_classrooms)
                for i in range(n_classrooms):
                    classroom = Subgroup(self, counter)
                    for pupil in pupils_in_classroom[i]:
                        classroom.append(pupil)
                        pupil.subgroups.primary_activity = classroom
                    self.subgroups.append(classroom)
                    counter += 1
            else:
                subgroup.subgroup_type = counter
                self.subgroups.append(subgroup)
                counter += 1
                self.years.append(year_age_group[idx])
        self.years = tuple(self.years)
        self.n_classrooms = len(self.subgroups) - 1

    @property
    def is_full(self):
        if self.n_pupils >= self.n_pupils_max:
            return True
        return False

    @property
    def n_pupils(self):
        return len(self.students)

    @property
    def n_teachers(self):
        return len(self.teachers)

    @property
    def teachers(self):
        return self.subgroups[self.SubgroupType.teachers]

    @property
    def students(self):
        ret = []
        for subgroup in self.subgroups[1:]:
            ret += subgroup.people
        return ret

    @property
    def super_area(self):
        if self.area is None:
            return None
        return self.area.super_area


class Schools(Supergroup):
    def __init__(
        self,
        schools: List["School"],
        school_trees: Optional[Dict[int, BallTree]] = None,
        agegroup_to_global_indices: dict = None,
    ):
        """
        Create a group of Schools, and provide functionality to access closest school

        Parameters
        ----------
        area_names
            list of areas for which to build schools
        schools:
            list of school instances
        school_tree:
            BallTree built on all schools coordinates
        agegroup_to_global_indices:
            dictionary to map the
        """
        super().__init__(members=schools)
        self.school_trees = school_trees
        self.school_agegroup_to_global_indices = agegroup_to_global_indices

    @classmethod
    def for_geography(
        cls,
        geography: Geography,
        data_file: str = default_data_filename,
        config_file: str = default_config_filename,
    ) -> "Schools":
        """
        Parameters
        ----------
        geography
            an instance of the geography class
        """
        return cls.for_areas(geography.areas, data_file, config_file)

    @classmethod
    def for_areas(
        cls,
        areas: Areas,
        data_file: str = default_data_filename,
        config_file: str = default_config_filename,
    ) -> "Schools":
        """
        Parameters
        ----------
        area_names
            list of areas for which to create populations
        data_path
            The path to the data directory
        config
        """
        return cls.from_file(areas, data_file, config_file)

    @classmethod
    def from_file(
        cls,
        areas: Areas,
        data_file: str = default_data_filename,
        config_file: str = default_config_filename,
    ) -> "Schools":
        """
        Initialize Schools from path to data frame, and path to config file 

        Parameters
        ----------
        filename:
            path to school dataframe
        config_filename:
            path to school config dictionary

        Returns
        -------
        Schools instance
        """
        school_df = pd.read_csv(data_file, index_col=0)
        area_names = [area.name for area in areas]
        if area_names is not None:
            # filter out schools that are in the area of interest
            school_df = school_df[school_df["oa"].isin(area_names)]
        school_df.reset_index(drop=True, inplace=True)
        logger.info(f"There are {len(school_df)} schools in this geography.")
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls.build_schools_for_areas(areas, school_df)  # , **config,)

    @classmethod
    def build_schools_for_areas(
        cls,
        areas: Areas,
        school_df: pd.DataFrame,
        age_range: Tuple[int, int] = (0, 19),
        employee_per_clients: Dict[str, int] = None,
    ) -> "Schools":
        """
        Parameters
        ----------
        area
        Returns
        -------
            An infrastructure of schools
        """
        employee_per_clients = employee_per_clients or {
            "primary": 30,
            "secondary": 30,
        }
        # build schools
        schools = []
        for school_name, row in school_df.iterrows():
            n_pupils_max = row["NOR"]
            school_type = row["sector"]
            if school_type is np.nan:
                school_type = list(employee_per_clients.keys())[0]
            coordinates = np.array(
                row[["latitude", "longitude"]].values, dtype=np.float64
            )
            area = areas.get_closest_area(coordinates)
            school = School(
                coordinates=coordinates,
                n_pupils_max=n_pupils_max,
                age_min=int(row["age_min"]),
                age_max=int(row["age_max"]),
                sector=row["sector"],
                area=area,
            )
            schools.append(school)
            area.schools.append(school)

        # link schools
        school_trees, agegroup_to_global_indices = Schools.init_trees(
            school_df, age_range
        )
        return Schools(
            schools,
            school_trees=school_trees,
            agegroup_to_global_indices=agegroup_to_global_indices,
        )

    @staticmethod
    def init_trees(school_df: pd.DataFrame, age_range: Tuple[int, int],) -> "Schools":
        """
        Create trees to easily find the closest school that
        accepts a pupil given their age

        Parameters
        ----------
        school_df:
            dataframe with school characteristics data
        """
        school_trees = {}
        school_agegroup_to_global_indices = {
            k: [] for k in range(int(age_range[0]), int(age_range[1]) + 1,)
        }
        # have a tree per age
        for age in range(int(age_range[0]), int(age_range[1]) + 1):
            _school_df_agegroup = school_df[
                (school_df["age_min"] <= age) & (school_df["age_max"] >= age)
            ]
            schools_coords = _school_df_agegroup[["latitude", "longitude"]].values
            if not schools_coords.size:
                logger.info(f"No school for the age {age} in this world.")
                continue
            school_trees[age] = Schools._create_school_tree(schools_coords)
            school_agegroup_to_global_indices[age] = _school_df_agegroup.index.values
        return school_trees, school_agegroup_to_global_indices

    @staticmethod
    def _create_school_tree(schools_coordinates: np.ndarray) -> BallTree:
        """
        Reads school location and sizes, it initializes a KD tree on a sphere,
        to query the closest schools to a given location.

        Parameters
        ----------
        school_df: 
            dataframe with school characteristics data

        Returns
        -------
        Tree to query nearby schools

        """
        school_tree = BallTree(np.deg2rad(schools_coordinates), metric="haversine")
        return school_tree

    def get_closest_schools(
        self, age: int, coordinates: Tuple[float, float], k: int
    ) -> int:
        """
        Get the k-th closest school to a given coordinate, that accepts pupils
        aged age

        Parameters
        ----------
        age:
            age of the pupil
        coordinates: 
            latitude and longitude
        k:
            k-th neighbour

        Returns
        -------
        ID of the k-th closest school, within school trees for 
        a given age group

        """
        school_tree = self.school_trees[age]
        coordinates_rad = np.deg2rad(coordinates).reshape(1, -1)
        k = min(k, school_tree.data.shape[0])
        distances, neighbours = school_tree.query(
            coordinates_rad, k=k, sort_results=True,
        )
        return neighbours[0]
