from typing import List
from collections import defaultdict
import logging
from random import shuffle
import numpy as np

from june.groups import University
from june.geography import Area, Areas
from june.demography import Population

logger = logging.getLogger("university_distributor")


class UniversityDistributor:
    def __init__(self, universities: List[University], max_radius = 15):
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
        self.max_radius = max_radius
        self.min_student_age = 19
        self.max_student_age = 24

    def find_students_in_areas(
        self, students_dict: dict, areas: Areas, university: University
    ):
        for area in areas:
            for household in area.households:
                if household.type == "student":
                    for student in household.residents:
                        if student.primary_activity is None:
                            students_dict["student"][student.id].append(university)
                elif household.type == "communal":
                    for person in household.residents:
                        if self.min_student_age <= person.age <= self.max_student_age:
                            if person.primary_activity is None:
                                students_dict["communal"][person.id].append(university)
                else:
                    for person in household.residents:
                        if self.min_student_age <= person.age <= self.max_student_age:
                            if person.primary_activity is None:
                                students_dict["other"][person.id].append(university)

    def distribute_students_to_universities(self, areas: Areas, people: Population):
        """
        For each university, search for students in nearby areas and allocate them to
        the university.
        """
        logger.info(f"Distributing students to universities")
        n_total_students = 0
        students_dict = defaultdict(lambda: defaultdict(list))
        # get students in areas
        for university in self.universities:
            close_areas, distances = areas.get_closest_areas(
                coordinates=university.coordinates,
                k=len(areas),
                return_distance=True,
            )
            close_areas = np.array(close_areas)[distances < self.max_radius]
            self.find_students_in_areas(
                students_dict=students_dict, areas=close_areas, university=university,
            )
        # shuffle lists first
        for key in students_dict:
            for student_id in students_dict[key]:
                shuffle(students_dict[key][student_id])
        # allocate students in student households first, then communal, then other
        for key in ["student", "communal", "other"]:
            for student_id, uni_candidates in students_dict[key].items():
                for uni in uni_candidates:
                    if uni.n_students < uni.n_students_max:
                        university.add(
                            people.get_from_id(student_id), subgroup="student"
                        )

        logger.info(
            f"Distributed {n_total_students} students to {len(self.universities)} universities"
        )
