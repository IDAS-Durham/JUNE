from typing import List

from june.groups import University
from june.demography.geography import SuperArea, SuperAreas


class UniversityDistributor:
    def __init__(self, universities: List[University], max_number_of_super_areas=20):
        """
        For each university it searches in the nearby super areas for students living
        in student households. Once it has enough to fill the university, it stops
        searching and fills the university.

        Parameters
        ----------
        universities
            a list of universities to fill
        max_number_of_super_areas
            maximum number of neighbour super areas to look for students
        """
        self.universities = universities
        self.max_number_of_super_areas = max_number_of_super_areas
        self.min_student_age = 19
        self.max_student_age = 24

    def find_students_in_super_areas(self, super_areas: SuperAreas, n_students: int):
        students = []
        students_in_communal = []
        students_in_normal_household = []
        for super_area in super_areas:
            for area in super_area.areas:
                for household in area.households:
                    if household.type == "student":
                        for student in household.people:
                            if student.primary_activity is None:
                                students.append(student)
                                if len(students) >= n_students:
                                    return students
                    elif household.type == "communal":
                        for person in household.people:
                            if self.min_student_age <= person.age <= self.max_student_age:
                                if person.primary_activity is None:
                                    students_in_communal.append(person)
                    else:
                        for person in household.people:
                            if self.min_student_age <= person.age <= self.max_student_age:
                                if person.primary_activity is None:
                                    students_in_normal_household.append(person)
        if len(students) < n_students:
            for person in students_in_communal:
                students.append(person)
                if len(students) >= n_students:
                    break

        if len(students) < n_students:
            for person in students_in_normal_household:
                students.append(person)
                if len(students) >= n_students:
                    break
        return students

    def distribute_students_to_universities(self, super_areas: SuperAreas):
        """
        For each university, search for students in nearby areas and allocate them to
        the university.
        """
        for university in self.universities:
            close_super_areas = super_areas.get_closest_super_areas(
                coordinates=university.coordinates,
                k=min(len(super_areas), self.max_number_of_super_areas),
                return_distance=False,
            )
            students = self.find_students_in_super_areas(
                close_super_areas, university.n_students_max
            )
            for student in students:
                university.add(student, subgroup="student")
