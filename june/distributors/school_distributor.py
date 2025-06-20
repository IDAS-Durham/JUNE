import logging
from typing import List, Tuple
import pandas as pd
import random
import numpy as np
import yaml

from june import paths
from june.geography import Area, SuperArea, Geography
from june.groups.school import Schools

default_config_filename = (
    paths.configs_path / "defaults/distributors/school_distributor.yaml"
)

logger = logging.getLogger("school_distributor")

EARTH_RADIUS = 6371  # km

default_decoder = {2314: "secondary", 2315: "primary", 2316: "special_needs"}


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
        teacher_student_ratio_primary=21,
        teacher_student_ratio_secondary=16,
        teacher_min_age=21,
        max_classroom_size=40,
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
        self.neighbour_schools = neighbour_schools
        self.school_age_range = age_range
        self.mandatory_school_age_range = mandatory_age_range
        self.education_sector_label = education_sector_label
        self.teacher_min_age = teacher_min_age
        self.teacher_student_ratio_primary = teacher_student_ratio_primary
        self.teacher_student_ratio_secondary = teacher_student_ratio_secondary
        self.max_classroom_size = max_classroom_size

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
            config["teacher_min_age"],
            config["max_classroom_size"],
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
        logger.info("Distributing kids to schools")
        for i, area in enumerate(areas):
            if i % 4000 == 0:
                logger.info(f"Distributed kids in {i} of {len(areas)} areas.")
            closest_schools_by_age = {}
            is_school_full = {}
            for agegroup in self.schools.school_trees:
                closest_schools = []
                closest_schools_idx = self.schools.get_closest_schools(
                    agegroup, area.coordinates, self.neighbour_schools
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
        logger.info("Kids distributed to schools")

        # Visualize the final distribution of kids to schools with a sample of Student IDs
        sample_data = []
        for school in random.sample(self.schools.members, min(10, len(self.schools.members))):
            # Get information about registered members
            total_registered = sum(len(members) for members in school.registered_members_ids.values())
            all_subgroups = list(school.registered_members_ids.keys())
            
            # Sample some IDs to display
            sampled_ids = []
            for subgroup, members in school.registered_members_ids.items():
                if members:
                    # Take up to 2 from each subgroup
                    for member_id in members[:2]:
                        sampled_ids.append(f"sg{subgroup}:{member_id}")
            
            sampled_ids = sampled_ids[:5]  # Limit to 5 total
            
            sample_data.append({
                "| School ID": school.id,
                "| Area": school.area.name if school.area else "Unknown Area",
                "| Total Students": len(school.students),
                "| Total Registered Members": total_registered,
                "| Subgroups": all_subgroups,
                "| Sample Registered Member IDs": sampled_ids
            })
        
        df_schools = pd.DataFrame(sample_data)
        print("\n===== Sample of Registered Members in Schools =====")
        print(df_schools)

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
                # remove from working population
                if person.work_super_area is not None:
                    person.work_super_area.remove_worker(person)
                school.add(person)
                # Add to registered members
                subgroup = 0 if person.age > school.age_max else person.age - school.age_min + 1
                school.add_to_registered_members(person.id, subgroup_type=subgroup)

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
                        if person.work_super_area is not None:
                            person.work_super_area.remove_worker(person)
                        school.add(person)
                        # Add to registered members
                        subgroup = 0 if person.age > school.age_max else person.age - school.age_min + 1
                        school.add_to_registered_members(person.id, subgroup_type=subgroup)

    def distribute_teachers_to_schools_in_super_areas(
        self, super_areas: List[SuperArea]
    ):
        for super_area in super_areas:
            self.distribute_teachers_to_school(super_area)

        classroom_distribution_data = []
        for super_area in super_areas:
            for area in super_area.areas:
                for school in area.schools:
                    # Gather data for each classroom (starting from index 1)
                    for classroom_id, classroom in enumerate(school.subgroups[1:], start=1):
                        if not classroom.people:
                            continue  # Skip empty classrooms
                        
                        classroom_distribution_data.append({
                            "| School ID": school.id if hasattr(school, 'id') else "Unknown",
                            "| Classroom ID": classroom_id,
                            "| Total Students in Classroom": len(classroom.people)
                        })

        # Convert data to a DataFrame for easy viewing
        df_classrooms = pd.DataFrame(classroom_distribution_data)
        print("\n===== Teacher Assignment to Schools =====")
        print(df_classrooms)

    def distribute_teachers_to_school(self, super_area: SuperArea):
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
        # separate schools in primary and secondary
        primary_schools = []
        secondary_schools = []
        for area in super_area.areas:
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
        # assign teacher to student ratios in schools
        for school in primary_schools:
            school.n_teachers_max = int(
                np.round(
                    school.n_pupils
                    / np.random.poisson(self.teacher_student_ratio_primary)
                )
            )
        for school in secondary_schools:
            school.n_teachers_max = int(
                np.round(
                    school.n_pupils
                    / np.random.poisson(self.teacher_student_ratio_secondary)
                )
            )

        np.random.shuffle(primary_schools)
        np.random.shuffle(secondary_schools)
        all_teachers = [
            person
            for person in super_area.workers
            if person.sector == self.education_sector_label
            and person.age > self.teacher_min_age
            and person.primary_activity is None
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
        while primary_teachers:
            all_filled = True
            for primary_school in primary_schools:
                if primary_school.n_pupils == 0:
                    continue
                if primary_school.n_teachers < primary_school.n_teachers_max:
                    all_filled = False
                    teacher = primary_teachers.pop()
                    if not primary_teachers:
                        all_filled = True
                        break
                    primary_school.add(teacher)
                    primary_school.add_to_registered_members(teacher.id, subgroup_type=0)  # Teachers are in subgroup 0
                    teacher.lockdown_status = "key_worker"
            if all_filled:
                break

        while secondary_teachers:
            all_filled = True
            for secondary_school in secondary_schools:
                if secondary_school.n_pupils == 0:
                    continue
                if secondary_school.n_teachers < secondary_school.n_teachers_max:
                    all_filled = False
                    teacher = secondary_teachers.pop()
                    if not secondary_teachers:
                        all_filled = True
                        break
                    secondary_school.add(teacher)
                    secondary_school.add_to_registered_members(teacher.id, subgroup_type=0)  # Teachers are in subgroup 0
                    teacher.lockdown_status = "key_worker"
            if all_filled:
                break

        remaining_teachers = primary_teachers + secondary_teachers + extra_teachers
        empty_schools = [
            school
            for school in primary_schools + secondary_schools
            if school.n_pupils > 0 and school.n_teachers == 0
        ]
        for school in empty_schools:
            if not remaining_teachers:
                break
            teacher = remaining_teachers.pop()
            school.add(teacher)
            school.add_to_registered_members(teacher.id, subgroup_type=0)  # Teachers are in subgroup 0
            teacher.lockdown_status = "key_worker"

        while remaining_teachers:
            all_filled = True
            for school in primary_schools + secondary_schools:
                if school.n_pupils == 0:
                    continue
                if school.n_teachers < school.n_teachers_max:
                    all_filled = False
                    teacher = remaining_teachers.pop()
                    if not remaining_teachers:
                        all_filled = True
                        break
                    school.add(teacher)
                    school.add_to_registered_members(teacher.id, subgroup_type=0)  # Teachers are in subgroup 0
                    teacher.lockdown_status = "key_worker"
            if all_filled:
                break

    def limit_classroom_sizes(
        self,
    ):
        """
        Limit subgroup sizes that represent class rooms to a maximum number of students.
        If maximum number is exceeded create new subgroups to distribute students homogeneously
        """
        for school in self.schools:
            school.limit_classroom_sizes(self.max_classroom_size)
        # Collect classroom data from all schools
        all_classroom_data = []
        for school in self.schools:
            for i, classroom in enumerate(school.subgroups[1:], start=1):  # Skip index 0 for teachers
                student_ids = [student.id for student in classroom.people]
                
                # Sample up to 5 student IDs for visualization
                sampled_student_ids = random.sample(student_ids, min(5, len(student_ids)))
                
                all_classroom_data.append({
                    "| School ID": school.id,
                    "| Classroom": f"{i}",
                    "| Total Students": len(classroom.people),
                    "| Sample of IDs of Persons (Students)": ", ".join(map(str, sampled_student_ids))
                })

        # Convert the data to a DataFrame for better visualization
        df_classrooms = pd.DataFrame(all_classroom_data)
        
        print("\n===== Classroom Distribution =====")
        print(df_classrooms)
