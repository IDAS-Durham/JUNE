from typing import List
from collections import defaultdict
import logging
import numpy as np
import pandas as pd
from random import randint

from june.groups.university import University, age_to_years
from june.geography import Areas
from june.demography import Population

logger = logging.getLogger("university_distributor")


class UniversityDistributor:
    def __init__(self, universities: List[University]):
        """
        For each university it searches in the nearby areas for students living
        in student households. Once it has enough to fill the university, it stops
        searching and fills the university.

        Parameters
        ----------
        universities
            a list of universities to fill
        max_number_of_areas
            maximum number of neighbour areas to look for students
        """
        self.universities = universities
        self.min_student_age = 19
        self.max_student_age = 24

    def find_students_in_areas(
        self, students_dict: dict, areas: Areas, university: University
    ):
        for area in areas:
            for household in area.households:
                if household.type == "student":
                    for student in household.residents:
                        if self.min_student_age <= student.age <= self.max_student_age:
                            if student.primary_activity is None:
                                students_dict[university.ukprn]["student"].append(
                                    student.id
                                )
                elif household.type == "communal":
                    for person in household.residents:
                        if self.min_student_age <= person.age <= self.max_student_age:
                            if person.primary_activity is None:
                                students_dict[university.ukprn]["communal"].append(
                                    person.id
                                )
                else:
                    for person in household.residents:
                        if self.min_student_age <= person.age <= self.max_student_age:
                            if person.primary_activity is None:
                                students_dict[university.ukprn]["other"].append(
                                    person.id
                                )

    def distribute_students_to_universities(self, areas: Areas, people: Population):
        """
        For each university, search for students in nearby areas and allocate them to
        the university.
        """
        logger.info("Distributing students to universities")
        need_more_students = True
        distance_increment = 10
        distance = 5
        while need_more_students and distance < 45:
            students_dict = self._build_student_dict(areas=areas, distance=distance)
            self._assign_students_to_unis(students_dict=students_dict, people=people)
            distance += distance_increment
            need_more_students = False
            for university in self.universities:
                if university.n_students < university.n_students_max:
                    need_more_students = True
                    break

        # Gather university data for visualization
        university_data = []
        for university in self.universities:
            # Get information about registered members
            total_registered = sum(len(members) for members in university.registered_members_ids.values())
            all_subgroups = list(university.registered_members_ids.keys())
            
            # Sample some IDs to display
            sampled_ids = []
            for subgroup, members in university.registered_members_ids.items():
                if members:
                    # Take up to 2 from each subgroup
                    for member_id in members[:2]:
                        sampled_ids.append(f"year{subgroup}:{member_id}")
            
            sampled_ids = sampled_ids[:5]  # Limit to 5 total
            
            university_data.append({
                "| University ID": university.id,
                "| Total Students": university.n_students,
                "| Total Registered Members": total_registered,
                "| Years": all_subgroups,
                "| Sample Registered Member IDs": sampled_ids,
                "| Max Capacity": university.n_students_max
            })

        # Convert the university data to a DataFrame for a structured view
        df_universities = pd.DataFrame(university_data)
        print("\n===== University Registered Members Summary =====")
        print(df_universities.head(10))  # Display a sample of 10 universities for brevity

        # Calculate the total number of students
        total_students = sum(university.n_students for university in self.universities)
        logger.info(f"Total number of students distributed across all universities: {total_students}")
        #for key, value in uni_info_dict.items():
        #    logger.info(f"University {key} has {value} students.")

    def _build_student_dict(self, areas, distance):
        students_dict = defaultdict(lambda: defaultdict(list))
        # get students in areas
        for university in self.universities:
            close_areas, distances = areas.get_closest_areas(
                coordinates=university.coordinates,
                k=min(len(areas), 1000),
                return_distance=True,
            )
            close_areas = np.array(close_areas)[distances < distance]
            self.find_students_in_areas(
                students_dict=students_dict, areas=close_areas, university=university
            )
        return students_dict

    def _assign_students_to_unis(self, students_dict, people):
        # Track already assigned students across all universities
        assigned_students = set()
        
        for key in ["student", "communal", "other"]:
            keep_key = True
            while keep_key:
                keep_key = False
                for university in self.universities:
                    # Filter out already assigned students from candidate list
                    student_candidates = [
                        student_id for student_id in students_dict[university.ukprn][key]
                        if student_id not in assigned_students
                    ]
                    
                    # Update the list in the dictionary
                    students_dict[university.ukprn][key] = student_candidates
                    
                    if student_candidates and not university.is_full:
                        student_id = student_candidates.pop()
                        # Mark this student as assigned
                        assigned_students.add(student_id)
                        
                        student = people.get_from_id(student_id)
                        university.add(student, subgroup="student")
                        
                        # Add to registered members
                        if student.age not in age_to_years:
                            year = randint(0, university.n_years - 1)
                        else:
                            year = age_to_years[student.age]
                        university.add_to_registered_members(student_id, subgroup_type=year)
                        keep_key = True
