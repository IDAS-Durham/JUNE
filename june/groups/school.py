from enum import IntEnum
from typing import List, Tuple, Dict, Optional

import numpy as np
import pandas as pd
import yaml
from sklearn.neighbors._ball_tree import BallTree

from june.groups.group import Group
from june.groups.group import Subgroup


class SchoolError(BaseException):
    """Class for throwing school related errors."""

    pass


class School(Group):
    class GroupType(IntEnum):
        teachers = 0
        students = 1

    __slots__ = (
        "id", "coordinates", "msoa", "n_pupils_max",
        "n_pupils", "age_min", "age_max", "age_structure",
        "sector", "is_full", "n_teachers_max", "n_teachers"
    )

    def __init__(
        self,
        school_id: int,
        coordinates: Tuple[float, float],
        n_pupils: int,
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

        number of groups N = age_max-age_min year +1 (student years) + 1 (teachers):
        0 - teachers
        1 - year of lowest age (age_min)
        ...
        n - year of highest age (age_max)
        """
        super().__init__(name="School_%05d" % school_id, spec="school")
        self.subgroups = [Subgroup() for _ in range(age_min, age_max + 2)]
        self.id = school_id
        self.coordinates = coordinates
        self.msoa = None
        self.n_pupils_max = n_pupils
        self.n_pupils = 0
        self.age_min = age_min
        self.age_max = age_max
        self.age_structure = {a: 0 for a in range(age_min, age_max + 1)}
        self.sector = sector
        self.is_full = False
        self.n_teachers_max = n_teachers_max
        self.n_teachers = 0

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
    # TODO: Many of these parameters are for the school distributor class, and should be put there
    # not here.
    def __init__(
        self,
        schools: List["School"],
        age_range: Tuple[int, int] = (0, 19),
        mandatory_age_range: Tuple[int, int] = (5, 18),
        student_nr_per_teacher: int = 30,
        school_tree: Optional[Dict[int, BallTree]] = None,
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

        self.members = []
        self.age_range = age_range
        self.mandatory_age_range = mandatory_age_range
        self.stud_nr_per_teacher = student_nr_per_teacher

        for school in schools:
            self.members.append(school)

        if school_tree is not None:
            self.school_trees = school_tree
            self.school_agegroup_to_global_indices = agegroup_to_global_indices

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

        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        school_df = pd.read_csv(filename, index_col=0)
        config = config["schools"]
        stud_nr_per_teacher = config["sub_sector"]["teacher_secondary"]["nr_of_clients"]
        # TODO: these del calls should be gone when we split the school config file from
        # the school distributor config file.
        del config["sub_sector"]
        del config["neighbour_schools"]
        del config["sector"]
        return cls.from_df(
            school_df,
            student_nr_per_teacher=stud_nr_per_teacher,
            **config,
        )

    @classmethod
    def from_df(
        cls,
        school_df: pd.DataFrame,
        age_range: Tuple[int, int] = (0, 19),
        mandatory_age_range: Tuple[int, int] = (5, 18),
        student_nr_per_teacher: int = 30,
    ):
        """
        Crates an instance of Schools from a dataframe. The optional kwargs are passed directly to the init function.

        Parameters
        ----------
        school_df:
            schools dataframe.
        Keyword Arguments:
            same as __init__ arguments.
        """
        school_df.reset_index(drop=True, inplace=True)
        schools = []
        for i, (index, row) in enumerate(school_df.iterrows()):
            n_teachers_max = int(row["NOR"] / student_nr_per_teacher)
            school = School(
                i,
                np.array(row[["latitude", "longitude"]].values, dtype=np.float64),
                row["NOR"],
                n_teachers_max,
                int(row["age_min"]),
                int(row["age_max"]),
                row["sector"],
            )
            schools.append(school)
        school_tree, agegroup_to_global_indices = cls.init_trees(
            cls, school_df, age_range 
        )

        return Schools(
            schools,
            age_range=age_range,
            mandatory_age_range=mandatory_age_range,
            student_nr_per_teacher=student_nr_per_teacher,
            school_tree=school_tree,
            agegroup_to_global_indices=agegroup_to_global_indices,
        )

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

