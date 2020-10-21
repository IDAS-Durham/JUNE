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
    def __init__(
        self, universities: List[University],
    ):
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
        logger.info(f"Distributing students to universities")
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
        uni_info_dict = {
            university.ukprn: university.n_students for university in self.universities
        }
        for key, value in uni_info_dict.items():
            logger.info(f"University {key} has {value} students.")

    def _build_student_dict(self, areas, distance):
        students_dict = defaultdict(lambda: defaultdict(list))
        # get students in areas
        for university in self.universities:
            close_areas, distances = areas.get_closest_areas(
                coordinates=university.coordinates, k=min(len(areas), 1000), return_distance=True,
            )
            close_areas = np.array(close_areas)[distances < distance]
            self.find_students_in_areas(
                students_dict=students_dict, areas=close_areas, university=university,
            )
        return students_dict

    def _assign_students_to_unis(self, students_dict, people):
        for key in ["student", "communal", "other"]:
            keep_key = True
            while keep_key:
                keep_key = False
                for university in self.universities:
                    student_candidates = students_dict[university.ukprn][key]
                    if student_candidates and not university.is_full:
                        student_id = student_candidates.pop()
                        university.add(
                            people.get_from_id(student_id), subgroup="student"
                        )
                        keep_key = True
