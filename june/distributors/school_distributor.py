import logging
from typing import List, Tuple

import numpy as np
import yaml
from scipy import stats

from june import paths
from june.demography.geography import Area, SuperArea, Geography
from june.groups.school import Schools

default_config_filename = (
    paths.configs_path / "defaults/distributors/school_distributor.yaml"
)

logger = logging.getLogger(__name__)

EARTH_RADIUS = 6371  # km

default_decoder = {
    2314: "secondary",
    2315: "primary",
    2316: "special_needs",
}


class SchoolDistributor:
    """
    Distributes students in an area to different schools 
    """

    def __init__(
        self,
        schools: Schools,
        education_sector_label="P",
        neighbour_schools: int = 35,
        age_range: Tuple[int, int] = (0, 19),
        mandatory_age_range: Tuple[int, int] = (5, 18),
        students_teacher_ratio=25,
        teacher_min_age=21,
    ):
        """
        Get closest schools to this output area, per age group
        (different schools admit pupils with different age ranges)

        Parameters
        ----------
        schools: 
            instance of Schools, with information on all schools in world.
        area:
            instance of Area.
        config:
            config dictionary.
        """
        self.schools = schools
        self.students_teacher_ratio = students_teacher_ratio
        self.neighbour_schools = neighbour_schools
        self.school_age_range = age_range
        self.mandatory_school_age_range = mandatory_age_range
        self.education_sector_label = education_sector_label
        self.teacher_min_age = teacher_min_age

    @classmethod
    def from_file(
        cls,
        schools: "Schools",
        config_filename: str = default_config_filename,
        # mandatory_age_range: Tuple[int, int] = (5, 18),#part of config ?
    ) -> "SchoolDistributor":
        """
        Initialize SchoolDistributor from path to its config file 

        Parameters
        ----------
        schools: 
            instance of Schools, with information on all schools in world.
        area:
            instance of Area.
        config:
            path to config dictionary

        Returns
        -------
        SchoolDistributor instance
        """
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        education_sector_label = SchoolDistributor.find_jobs(config)
        return SchoolDistributor(
            schools,
            education_sector_label,
            config["neighbour_schools"],
            config["age_range"],
            config["mandatory_age_range"],
            config["teacher_min_age"]
        )

    @classmethod
    def from_geography(
        cls, geography: Geography, config_filename: str = default_config_filename
    ):
        return cls.from_file(geography.schools, config_filename)

    @staticmethod
    def find_jobs(config: dict):
        education_sector_label = []
        for value1 in config.values():
            if isinstance(value1, dict):
                for value2 in value1.values():
                    education_sector_label.append(value2["sector_id"])
        return education_sector_label

    def distribute_kids_to_school(self, areas: List[Area]):
        """
        Function to distribute kids to schools according to distance 
        """
        for area in areas:
            closest_schools_by_age = {}
            is_school_full = {}
            for agegroup in self.schools.school_trees:
                closest_schools = []
                closest_schools_idx = self.schools.get_closest_schools(
                    agegroup, area.coordinates, self.neighbour_schools,
                )
                for idx in closest_schools_idx:
                    real_idx = self.schools.school_agegroup_to_global_indices[agegroup][
                        idx
                    ]
                    closest_schools.append(self.schools.members[real_idx])
                closest_schools_by_age[agegroup] = closest_schools
                is_school_full[agegroup] = False
            self.distribute_mandatory_kids_to_school(
                area, is_school_full, closest_schools_by_age
            )
            self.distribute_non_mandatory_kids_to_school(
                area, is_school_full, closest_schools_by_age
            )

    def distribute_mandatory_kids_to_school(
        self, area: Area, is_school_full: dict, closest_schools_by_age: dict
    ):
        """
        Send kids to the nearest school among the self.neighbour_schools,
        that has vacancies. If none of them has vacancies, pick one of them
        at random (making it larger than it should be)
        """
        for person in area.people:
            if (
                person.age <= self.mandatory_school_age_range[1]
                and person.age >= self.mandatory_school_age_range[0]
            ):
                if person.age not in is_school_full:
                    continue
                if is_school_full[person.age]:
                    random_number = np.random.randint(
                        0,
                        min(
                            len(closest_schools_by_age[person.age]),
                            self.neighbour_schools,
                        ),
                    )
                    school = closest_schools_by_age[person.age][random_number]
                else:
                    schools_full = 0
                    for i in range(self.neighbour_schools):  # look for non full school
                        if i >= len(closest_schools_by_age[person.age]):
                            break
                        school = closest_schools_by_age[person.age][i]
                        if school.n_pupils >= school.n_pupils_max:
                            schools_full += 1
                        else:
                            break

                        is_school_full[person.age] = True
                        random_number = np.random.randint(
                            0,
                            min(
                                len(closest_schools_by_age[person.age]),
                                self.neighbour_schools,
                            ),
                        )
                        school = closest_schools_by_age[person.age][random_number]
                    else:  # just keep the school saved in the previous for loop
                        pass
                school.add(person, school.SubgroupType.students)

    def distribute_non_mandatory_kids_to_school(
        self, area: Area, is_school_full: dict, closest_schools_by_age: dict
    ):
        """
        For kids in age ranges that might go to school, but it is not mandatory
        send them to the closest school that has vacancies among the self.max_schools closests.
        If none of them has vacancies do not send them to school
        """
        for person in area.people:
            if (
                self.school_age_range[0]
                < person.age
                < self.mandatory_school_age_range[0]
                or self.mandatory_school_age_range[1]
                < person.age
                < self.school_age_range[1]
            ):
                if person.age not in is_school_full or is_school_full[person.age]:
                    continue
                else:
                    find_school = False
                    for i in range(self.neighbour_schools):  # look for non full school
                        if i >= len(closest_schools_by_age[person.age]):
                            # TEST THIS
                            break
                        school = closest_schools_by_age[person.age][i]
                        # check number of students in that age group
                        yearindex = person.age - school.age_min + 1
                        n_pupils_age = len(school.subgroups[yearindex].people)
                        if (school.n_pupils < school.n_pupils_max) and (
                            n_pupils_age
                            < (school.n_pupils_max / (school.age_max - school.age_min))
                        ):
                            find_school = True
                            break
                    if find_school:
                        school.add(person, school.SubgroupType.students)

    def distribute_teachers_to_schools_in_super_areas(
        self, super_areas: List[SuperArea]
    ):
        for msoarea in super_areas:
            self.distribute_teachers_to_school(msoarea)

    def distribute_teachers_to_school(self, msoarea: SuperArea):
        """
        Assigns teachers to super area. The strategy is the following:
        we loop over the schools to divide them into two subgroups,
        primary schools and secondary schools. If a school is both, then
        we assign it randomly to one of the two.
        Then we loop over the workers in the super area to find the teachers,
        which we also divide into two subgroups analogously to the schools.
        We assign the teachers to the schools following a fix student to teacher ratio.
        We put a lower age limit to teachers at the age of 21.
        """
        primary_schools = []
        secondary_schools = []
        for area in msoarea.areas:
            for school in area.schools:
                if school.n_pupils == 0:
                    continue
                # note one school can be primary and secondary.
                if type(school.sector) != str:
                    idx = np.random.randint(0, 2)
                    if idx == 0:
                        primary_schools.append(school)
                    else:
                        secondary_schools.append(school)
                else:
                    if "primary" in school.sector:
                        if "secondary" in school.sector:
                            idx = np.random.randint(0, 2)
                            if idx == 0:
                                primary_schools.append(school)
                            else:
                                secondary_schools.append(school)
                        else:
                            primary_schools.append(school)
                    elif "secondary" in school.sector:
                        secondary_schools.append(school)
                    else:
                        idx = np.random.randint(0, 2)
                        if idx == 0:
                            primary_schools.append(school)
                        else:
                            secondary_schools.append(school)
        np.random.shuffle(primary_schools)
        np.random.shuffle(secondary_schools)
        all_teachers = [
            person
            for person in msoarea.workers
            if person.sector == self.education_sector_label and person.age > self.teacher_min_age and person.primary_activity is None
        ]
        primary_teachers = []
        secondary_teachers = []
        extra_teachers = []
        for teacher in all_teachers:
            if teacher.sub_sector == "teacher_primary":
                primary_teachers.append(teacher)
            elif teacher.sub_sector == "teacher_secondary":
                secondary_teachers.append(teacher)
            else:
                extra_teachers.append(teacher)
        np.random.shuffle(primary_teachers)
        np.random.shuffle(secondary_teachers)
        np.random.shuffle(extra_teachers)
        schools_without_teachers = []
        for primary_school in primary_schools:
            n_students = len(primary_school.students)
            if n_students == 0:
                continue
            n_teachers = max(int(np.floor(n_students / self.students_teacher_ratio)), 1)
            for _ in range(n_teachers):
                if primary_teachers:
                    teacher = primary_teachers.pop()
                elif extra_teachers:
                    teacher = extra_teachers.pop()
                else:
                    schools_without_teachers.append(primary_school)
                    break
                primary_school.add(teacher, school.SubgroupType.teachers)
                teacher.lockdown_status = 'key_worker'

        for secondary_school in secondary_schools:
            n_students = len(secondary_school.students)
            if n_students == 0:
                continue
            n_teachers = max(int(np.floor(n_students / self.students_teacher_ratio)), 1)
            for _ in range(n_teachers):
                if secondary_teachers:
                    teacher = secondary_teachers.pop()
                elif extra_teachers:
                    teacher = extra_teachers.pop()
                else:
                    schools_without_teachers.append(secondary_school)
                    break
                secondary_school.add(teacher, school.SubgroupType.teachers)
                teacher.lockdown_status = 'key_worker'

        remaining_teachers = primary_teachers + secondary_teachers + extra_teachers
        if schools_without_teachers:
            for i in range(len(remaining_teachers)):
                teacher = remaining_teachers[i]
                school_idx = i % len(schools_without_teachers)
                school = schools_without_teachers[school_idx]
                if school.n_pupils / school.n_teachers <= self.students_teacher_ratio:
                    continue
                school.add(
                    teacher, school.SubgroupType.teachers
                )
                teacher.lockdown_status = 'key_worker'
