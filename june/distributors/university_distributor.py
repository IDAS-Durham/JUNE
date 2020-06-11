from typing import List

from june.groups import University
from june.demography.geography import SuperArea, SuperAreas


class UniversityDistributor:
    def __init__(self, universities: List[University], max_number_of_super_areas=10):
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

    def find_students_in_super_areas(self, super_areas: SuperAreas, n_students: int):
        students = []
        for super_area in super_areas:
            for area in super_area.areas:
                for household in area.households:
                    if household.type == "student":
                        for student in household.people:
                            students.append(student)
                            if len(students) >= n_students:
                                return students
        return students

    def distribute_students_to_universities(self, super_areas: SuperAreas):
        for university in self.universities:
            close_super_areas = super_areas.get_closest_super_areas(
                coordinates=university.coordinates,
                k=min(len(super_areas), self.max_number_of_super_areas),
                return_distance=False,
            )
            students = self.find_students_in_super_areas(close_super_areas, university.n_students_max)
            for student in students:
                university.add(student, subgroup="student")



