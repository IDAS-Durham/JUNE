import os
from enum import IntEnum
from itertools import count
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import numpy as np
import pandas as pd
import yaml
from sklearn.neighbors._ball_tree import BallTree

from june.geography import Geography
from june.groups.group import Group
from june.groups.group import Subgroup
import logging

logger = logging.getLogger(__name__)

default_data_filename = Path(os.path.abspath(__file__)).parent.parent.parent / \
                        "data/processed/school_data/england_schools_data.csv"
default_areas_map_path = Path(os.path.abspath(__file__)).parent.parent.parent / \
                         "data/processed/geographical_data/oa_msoa_region.csv"
default_config_filename = Path(os.path.abspath(__file__)).parent.parent.parent / \
                          "configs/defaults/groups/schools.yaml"


class SchoolError(BaseException):
    pass


class School(Group):
    _id = count()
    __slots__ = (
        "id", "coordinates", "super_area",
        "n_pupils_max", "n_pupils", "n_teachers_max", "n_teachers",
        "age_min", "age_max", "age_structure",
        "sector", "is_full"
    )

    class GroupType(IntEnum):
        teachers = 0
        students = 1

    def __init__(
            self,
            school_id,
            coordinates: Tuple[float, float],
            n_pupils_max: int,
            n_teachers_max: int,
            age_min: int,
            age_max: int,
            sector: str,
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

        number of SubGroups N = age_max-age_min year +1 (student years) + 1 (teachers):
        0 - teachers
        1 - year of lowest age (age_min)
        ...
        n - year of highest age (age_max)
        """
        super().__init__()
        self.id = school_id
        self.subgroups = [Subgroup() for _ in range(age_min, age_max + 2)]
        self.coordinates = coordinates
        self.super_area = None
        self.n_pupils = 0
        self.n_teachers = 0
        self.n_pupils_max = n_pupils_max
        self.n_teachers_max = n_teachers_max
        self.is_full = False
        self.age_min = age_min
        self.age_max = age_max
        self.age_structure = {a: 0 for a in range(age_min, age_max + 1)}
        self.sector = sector

    def add(self, person, qualifier=GroupType.students):
        if qualifier == self.GroupType.students:
            self.subgroups[1 + person.age - self.age_min].append(person)
            person.school = self
            person.groups.append(self)
        else:
            super().add(
                person,
                qualifier
            )
            person.groups.append(self)
            super().add(person, qualifier)


class Schools:

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

        self.members = schools
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
        area_names = [area.name for area in geography.areas]
        if len(area_names) == 0:
            raise SchoolError("Empty geography!")
        return cls.for_areas(area_names, data_file, config_file)

    @classmethod
    def for_zone(
            cls,
            filter_key: Dict[str, list],
            areas_maps_path: str = default_areas_map_path,
            data_file: str = default_data_filename,
            config_file: str = default_config_filename,
    ) -> "Schools":
        """
        
        Example
        -------
            filter_key = {"region" : "North East"}
            filter_key = {"msoa" : ["EXXXX", "EYYYY"]}
        """
        if len(filter_key.keys()) > 1:
            raise NotImplementedError("Only one type of area filtering is supported.")
        geo_hierarchy = pd.read_csv(areas_maps_path)
        zone_type, zone_list = filter_key.popitem()
        area_names = geo_hierarchy[geo_hierarchy[zone_type].isin(zone_list)]["oa"]
        if len(area_names) == 0:
            raise SchoolError("Region returned empty area list.")
        return cls.for_areas(area_names, data_file, config_file)

    @classmethod
    def for_areas(
            cls,
            area_names: List[str],
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
        return cls.from_file(area_names, data_file, config_file)

    @classmethod
    def from_file(
            cls,
            area_names: Optional[List[str]] = [],
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
        school_df.reset_index(drop=True, inplace=True)
        if len(area_names) is not 0:
            # filter out schools that are in the area of interest
            school_df = school_df[school_df["oa"].isin(area_names)]

        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls.build_schools_for_areas(
            school_df,
            **config,
        )

    @classmethod
    def build_schools_for_areas(
            cls,
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

        for _, row in school_df.iterrows():
            n_pupils_max = row["NOR"]
            school_type = row["sector"]
            if school_type is np.nan:  # TODO double check dataframe
                school_type = list(employee_per_clients.keys())[0]
            n_teachers_max = int(n_pupils_max / employee_per_clients[school_type])
            school = School(
                8637,
                np.array(row[["latitude", "longitude"]].values, dtype=np.float64),
                n_pupils_max,
                n_teachers_max,
                int(row["age_min"]),
                int(row["age_max"]),
                row["sector"],
            )
            schools.append(school)

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
    def init_trees(
            school_df: pd.DataFrame,
            age_range: Tuple[int, int],
    ) -> "Schools":
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
            k: [] for k in range(int(age_range[0]), int(age_range[1]) + 1, )
        }
        # have a tree per age
        for age in range(int(age_range[0]), int(age_range[1]) + 1):
            _school_df_agegroup = school_df[
                (school_df["age_min"] <= age) & (school_df["age_max"] >= age)
                ]
            schools_coords = _school_df_agegroup[["latitude", "longitude"]].values
            if len(schools_coords) is 0:
                logger.info(f"No school for the age {age} in this world.")
                continue
            school_trees[age] = Schools._create_school_tree(
                schools_coords
            )
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
        school_tree = BallTree(
            np.deg2rad(schools_coordinates), metric="haversine"
        )
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
        distances, neighbours = school_tree.query(
            coordinates_rad, k=k, sort_results=True,
        )
        return neighbours[0]

    def __len__(self):
        return len(self.members)

    def __iter__(self):
        return iter(self.members)


if __name__ == '__main__':
    geography = Geography.from_file(filter_key={"msoa": ["E02004935"]})
    schools = Schools.for_geography(geography)
    school = schools.members[0]
    print(int(0.5 * (school.age_min + school.age_max)))
    print(school.GroupType.teachers == 0)
    print(bool(school.subgroups[school.GroupType.teachers].people))
    # schools = Schools.for_zone({"region": ["North East"]})
