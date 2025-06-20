import logging
import numba as nb
import math
import random
from enum import IntEnum
from copy import deepcopy
from june import paths
from typing import List, Tuple, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from june.epidemiology.infection.disease_config import DiseaseConfig
from june.geography import Geography, Areas, Area
from june.groups import Group, Subgroup, Supergroup
from june.groups.group.interactive import InteractiveGroup


default_data_filename = paths.data_path / "input/schools/england_schools.csv"
default_areas_map_path = paths.data_path / "input/geography/area_super_area_region.csv"
default_config_filename = paths.configs_path / "defaults/groups/schools.yaml"

logger = logging.getLogger("schools")


class SchoolError(BaseException):
    pass


class SchoolClass(Subgroup):
    def __init__(self, group, subgroup_type: int):
        super().__init__(group, subgroup_type)
        self.quarantine_starting_date = -np.inf


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
        "disease_config",
        "registered_members_ids",
    )

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
        registered_members_ids: dict = None
    ):
        """
        Create a School given its description.

        Parameters
        ----------
        ...
        disease_config:
            Configuration object for the disease.
        """

        super().__init__()
        self.subgroups = []
        if n_classrooms is None:
            n_classrooms = age_max - age_min
        self.subgroups = [SchoolClass(self, i) for i in range(n_classrooms + 2)]

        self.n_classrooms = n_classrooms
        self.coordinates = coordinates
        self.area = area
        self.n_pupils_max = n_pupils_max
        self.n_teachers_max = None
        self.age_min = age_min
        self.age_max = age_max
        self.sector = sector
        self.years = tuple(range(age_min, age_max + 1)) if years is None else tuple(years)
        self.registered_members_ids = registered_members_ids if registered_members_ids is not None else {}

    def get_interactive_group(self, people_from_abroad=None):
        return InteractiveSchool(self, people_from_abroad=people_from_abroad)

    def add(self, person):
        if person.age <= self.age_max:
            subgroup = self.subgroups[1 + person.age - self.age_min]
            subgroup.append(person)
            person.subgroups.primary_activity = subgroup
        else:  # teacher
            subgroup = self.subgroups[0]
            subgroup.append(person)
            person.subgroups.primary_activity = subgroup
            
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
                    classroom = SchoolClass(self, counter)
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
    venue_class = School

    def __init__(
        self,
        schools: List["venue_class"],
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
        Creates Schools for the given geography with a disease configuration.
        """
        schools = cls.for_areas(
            geography.areas,
            data_file,
            config_file
        )

        # Sample 5 schools from each area for visualization
        sampled_schools = []
        for area in geography.areas:
            if hasattr(area, 'schools') and area.schools:
                # Sample 5 schools or fewer if there are less than 5
                sample_schools = random.sample(area.schools, min(5, len(area.schools)))
                for school in sample_schools:
                    sampled_schools.append({
                        "| School ID": school.id,
                        "| Area": area.name,
                        "| School Sector": school.sector,
                        "| Number of Pupils": school.n_pupils,
                        "| Coordinates": school.coordinates,
                        "| Max Pupils": school.n_pupils_max,
                        "| Min Age": school.age_min,
                        "| Max Age": school.age_max
                    })

        # Convert the sample data to a DataFrame
        df_schools = pd.DataFrame(sampled_schools)
        print("\n===== Sample of Created Schools =====")
        print(df_schools)
        
        logger.info(f"Created {len(schools)} schools in this geography.")
        return schools

    @classmethod
    def for_areas(
        cls,
        areas: Areas,
        data_file: str = default_data_filename,
        config_file: str = default_config_filename,
    ) -> "Schools":
        """
        Creates Schools for specified areas using a disease configuration.
        """
        return cls.from_file(areas, data_file, )

    @classmethod
    def from_file(
        cls,
        areas: Areas,
        data_file: str = default_data_filename,
    ) -> "Schools":
        """
        Initialize Schools from a data frame and a disease configuration.
        """

        school_df = pd.read_csv(data_file, index_col=0)
        area_names = [area.name for area in areas]
        if area_names is not None:
            school_df = school_df[school_df["oa"].isin(area_names)]
        school_df.reset_index(drop=True, inplace=True)
        logger.info(f"There are {len(school_df)} schools in this geography.")
        return cls.build_schools_for_areas(areas, school_df)

    @classmethod
    def build_schools_for_areas(
        cls,
        areas: Areas,
        school_df: pd.DataFrame,
        age_range: Tuple[int, int] = (0, 19),
        employee_per_clients: Dict[str, int] = None,
    ) -> "Schools":
        """
        Build schools for specified areas with disease configuration.
        """

        employee_per_clients = employee_per_clients or {"primary": 30, "secondary": 30}
        schools = []
        for school_name, row in school_df.iterrows():
            n_pupils_max = row["NOR"]
            school_type = row["sector"] if row["sector"] is not np.nan else list(employee_per_clients.keys())[0]
            coordinates = np.array(row[["latitude", "longitude"]].values, dtype=np.float64)
            area = areas.get_closest_area(coordinates)
            school = cls.venue_class(
                coordinates=coordinates,
                n_pupils_max=n_pupils_max,
                age_min=int(row["age_min"]),
                age_max=int(row["age_max"]),
                sector=school_type,
                area=area
            )
            schools.append(school)
            area.schools.append(school)

        school_trees, agegroup_to_global_indices = Schools.init_trees(school_df, age_range)
        return Schools(
            schools,
            school_trees=school_trees,
            agegroup_to_global_indices=agegroup_to_global_indices,
        )

    @staticmethod
    def init_trees(school_df: pd.DataFrame, age_range: Tuple[int, int]) -> "Schools":
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
            k: [] for k in range(int(age_range[0]), int(age_range[1]) + 1)
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
            coordinates_rad, k=k, sort_results=True
        )
        return neighbours[0]

    @property
    def n_teachers(self):
        return sum([school.n_teachers for school in self.members])

    @property
    def n_pupils(self):
        return sum([school.n_pupils for school in self.members])


@nb.jit(nopython=True)
def _translate_school_subgroup(idx, school_years):
    if idx > 0:
        idx = school_years[idx - 1] + 1
    return idx


class InteractiveSchool(InteractiveGroup):
    def __init__(self, group: "Group", people_from_abroad=None):
        super().__init__(group=group, people_from_abroad=people_from_abroad)
        self.school_years = group.years
        self.sector = group.sector

    @classmethod
    def get_raw_contact_matrix(
        cls, contact_matrix, alpha_physical, proportion_physical, characteristic_time
    ):
        """
        Creates a global contact matrix for school, which is by default 20x20, to take into account
        all possible school years combinations. Each school will then use a slice of this matrix.
        We assume that the number of contacts between two different school years goes as
        $ xi**abs(age_difference_between_school_years) * contacts_between_students$
        Teacher contacts are left as specified in the config file.
        """
        xi = 0.3
        age_min = 0
        age_max = 30
        n_subgroups_max = (age_max - age_min) + 2  # adding teachers
        age_differences = np.subtract.outer(
            range(age_min, age_max + 1), range(age_min, age_max + 1)
        )
        processed_contact_matrix = np.zeros((n_subgroups_max, n_subgroups_max))
        processed_contact_matrix[0, 0] = contact_matrix[0][0]
        processed_contact_matrix[0, 1:] = contact_matrix[0][1]
        processed_contact_matrix[1:, 0] = contact_matrix[1][0]
        processed_contact_matrix[1:, 1:] = (
            xi ** abs(age_differences) * contact_matrix[1][1]
        )
        physical_ratios = np.zeros((n_subgroups_max, n_subgroups_max))
        physical_ratios[0, 0] = proportion_physical[0][0]
        physical_ratios[0, 1:] = proportion_physical[0][1]
        physical_ratios[1:, 0] = proportion_physical[1][0]
        physical_ratios[1:, 1:] = proportion_physical[1][1]
        # add physical contacts
        processed_contact_matrix = processed_contact_matrix * (
            1.0 + (alpha_physical - 1.0) * physical_ratios
        )
        processed_contact_matrix *= 24 / characteristic_time
        # If same age but different class room, reduce contacts
        return processed_contact_matrix

    def get_processed_contact_matrix(self, contact_matrix):
        n_school_years = len(self.school_years)
        n_subgroups = n_school_years + 1
        ret = np.zeros((n_subgroups, n_subgroups))
        for i in range(0, n_subgroups):
            for j in range(0, n_subgroups):
                if i == j:
                    if i != 0:
                        ret[i, j] = contact_matrix[1, 1]
                    else:
                        ret[0, 0] = contact_matrix[0, 0]
                else:
                    if i == 0:
                        ret[0, j] = contact_matrix[0][1] / n_school_years
                    elif j == 0:
                        ret[i, 0] = contact_matrix[1][0] / n_school_years
                    else:
                        year_idx_i = _translate_school_subgroup(i, self.school_years)
                        year_idx_j = _translate_school_subgroup(j, self.school_years)
                        if year_idx_i == year_idx_j:
                            ret[i, j] = contact_matrix[year_idx_i, year_idx_j] / 4
                        else:
                            ret[i, j] = contact_matrix[year_idx_i, year_idx_j]
        return ret

    def get_processed_beta(self, betas, beta_reductions):
        """
        Returns the processed contact intensity, by taking into account the policies
        beta reductions and regional compliance. This is a group method as different interactive
        groups may choose to treat this differently.
        """
        if self.sector is None:
            spec = "school"
        elif "secondary" in self.sector:
            spec = "secondary_school"
        else:
            spec = "primary_school"
        if spec in betas:
            beta = betas[spec]
        else:
            beta = betas["school"]
        if spec in beta_reductions:
            beta_reduction = beta_reductions[spec]
        else:
            beta_reduction = beta_reductions.get("school", 1.0)
        try:
            regional_compliance = self.super_area.region.regional_compliance
        except AttributeError:
            regional_compliance = 1
        try:
            lockdown_tier = self.super_area.region.policy["lockdown_tier"]
            if lockdown_tier is None:
                lockdown_tier = 1
        except Exception:
            lockdown_tier = 1
        if int(lockdown_tier) == 4:
            tier_reduction = 0.5
        else:
            tier_reduction = 1.0

        return beta * (1 + regional_compliance * tier_reduction * (beta_reduction - 1))
