import os
import yaml
from enum import IntEnum
from pathlib import Path
from itertools import count
from typing import List, Tuple, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.neighbors._ball_tree import BallTree

from june.groups.group import Group
from june.groups.group import Subgroup
from june.logger_creation import logger

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
        "id", "coordinates", "msoa", "n_pupils_max",
        "n_pupils", "age_min", "age_max", "age_structure",
        "sector", "is_full", "n_teachers_max", "n_teachers"
    )

    class GroupType(IntEnum):
        teachers = 0
        students = 1

    def __init__(
        self,
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
        school_id:
            unique identifier of the school
        coordinates:
            latitude and longitude 
        n_pupils: 
            number of pupils that attend the school
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
        self.id = next(self._id)
        super().__init__(name="School_%05d" % self.id, spec="school")
        self.subgroups = [Subgroup() for _ in range(age_min, age_max + 2)]
        self.n_pupils_max = n_pupils_max
        self.n_teachers_max = n_teachers_max
        self.is_full = False
        self.age_min = age_min
        self.age_max = age_max
        self.age_structure = {a: 0 for a in range(age_min, age_max + 1)}
        self.sector = sector
        self.coordinates = coordinates
        self.super_area = None

    def add(self, person, qualifier=GroupType.students):
        if qualifier == self.GroupType.students:
            self.subgroups[1 + person.age - self.age_min].append(person)
            person.school = self
        else:
            super().add(person, qualifier)



class Schools:
    # TODO: Many of these parameters are for the school distributor class, and should be put there
    # not here.
    def __init__(
        self,
        area_names,
        schools: List["School"],
        school_trees: Optional[Dict[int, BallTree]] = None,
        agegroup_to_global_indices: dict = None,

    ):
        """
        Create a group of Schools, and provide functionality to access closest school

        Parameters
        ----------
        schools:
            list of school instances
        age_range:
           tuple containing minimum and maximum age of pupils 
        mandator_age_range:
           tuple containing minimum and maximum mandatory age of pupils 
        student_nr_per_teacher:
            number of students for one teacher
        school_tree:
            BallTree built on all schools coordinates
        agegroup_to_global_indices:
            dictionary to map the
        """

        self.members = schools
        self.age_range = age_range
        self.stud_nr_per_teacher = student_nr_per_teacher
        self.school_trees = school_trees
        self.school_agegroup_to_global_indices = agegroup_to_global_indices


    @classmethod
    def for_areas(
        cls,
        area_names: List[str],
        data_path: str = default_data_path,
        config: Optional[dict] = None,
    ) -> "Schools":
        """
        Load data from files and construct classes capable of generating demographic
        data for individuals in the population.
        Parameters
        ----------
        area_names
            list of areas for which to create populations
        data_path
            The path to the data directory
        config
            Optional configuration. At the moment this just gives an asymptomatic
            ratio.
        Returns
        -------
        A demography representing the super area
        """
        area_names = area_names
        age_structure_path = data_path / "age_structure_single_year.csv"
        female_fraction_path = data_path / "female_ratios_per_age_bin.csv"
        age_sex_generators = _load_age_and_sex_generators(
            age_structure_path, female_fraction_path, area_names
        )
        return Schools(age_sex_generators=age_sex_generators, area_names=area_names)


    @classmethod
    def for_zone(
        cls,
        filter_key: Dict[str, list],
        data_path: str = default_data_path,
        areas_maps_path: str = default_areas_map_path,
        config: Optional[dict] = None,
    ) -> "Schools":
        """
        Initializes a geography for a specific list of zones. The zones are
        specified by the filter_dict dictionary where the key denotes the kind
        of zone, and the value is a list with the different zone names. 
        
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
            raise DemographyError("Region returned empty area list.")
        return cls.for_areas(area_names, data_path, config)


    @classmethod
    def from_file(cls, filename: str, config_filename: str) -> "Schools":
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
        school_df = pd.read_csv(filename, index_col=0)
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        print("***", config)
        return cls.from_df(
            school_df,
            **config,
        )

    @classmethod
    def from_df(
        cls,
        school_df: pd.DataFrame,
        age_range: Tuple[int, int] = (0, 19),
        employee_per_clients: Optional[Dict[str, int]] = {
            "primary": 30,
            "secondary": 30,
        },
    ) -> "Schools":
        """
        Crates an instance of Schools from a dataframe. The optional kwargs
        are passed directly to the init function.

        Parameters
        ----------
        school_df:
            schools dataframe.
        Keyword Arguments:
            same as __init__ arguments.
        
        Returns
        -------
        Schools instance
        """
        school_df.reset_index(drop=True, inplace=True)
        schools = []

        # create schools
        for _ , row in school_df.iterrows():
            nr_of_students = row["NOR"]
            school_type = row["sector"]
            n_teachers = int(nr_of_students / employee_per_clients[school_type])
            school = School(
                np.array(row[["latitude", "longitude"]].values, dtype=np.float64),
                n_pupils_max,
                n_teachers_max,
                int(row["age_min"]),
                int(row["age_max"]),
                row["sector"],
            )
            schools.append(school)

        # relate schools
        school_tree, agegroup_to_global_indices = cls.init_trees(
            cls, school_df, age_range 
        )

        return Schools(
            schools,
            school_tree=school_tree,
            agegroup_to_global_indices=agegroup_to_global_indices,
        )


    #@classmethod
    #def for_zone(
    #    cls,
    #    data_path: str = default_data_path,
    #    areas_maps_path: str = default_areas_map_path,
    #    config: Optional[dict] = None,
    #) -> "Schools":


    def init_trees(self, school_df: pd.DataFrame, age_range: Tuple[int, int]):
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
            school_trees[age] = self._create_school_tree(self, _school_df_agegroup)
            school_agegroup_to_global_indices[age] = _school_df_agegroup.index.values

        return school_trees, school_agegroup_to_global_indices

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

    def _create_school_tree(self, school_df: pd.DataFrame) -> BallTree:
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
            np.deg2rad(school_df[["latitude", "longitude"]].values), metric="haversine"
        )
        return school_tree

    def __len__(self):
        return len(self.school)

    def __iter__(self):
        return iter(self.school)


if __name__ == '__main__':
    schools = Schools.from_file(
        filename = default_data_filename,
        config_filename = default_config_filename, 
    )


    schools = Schools.for_regions(["North East"])
    for area in demography.area_names:
        schools.population_for_area(area)
