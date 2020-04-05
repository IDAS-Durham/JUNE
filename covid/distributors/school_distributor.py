import numpy as np
from random import uniform
from scipy import stats
import warnings

EARTH_RADIUS = 6371  # km

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""


class SchoolError(BaseException):
    """Class for throwing household related errors."""

    pass


class SchoolDistributor:
    """
    Distributes students to different schools
    """

    def __init__(self, area):
        self.area = area
        self.MAX_SCHOOLS = 6
        self.age_means = {}
        for agegroup_id, agegroup in area.world.decoder_age.items():
            try:
                age_1, age_2 = agegroup.split("-")
                if age_2 == 'XXX':
                    agemean = 90
                else:
                    age_1 = float(age_1)
                    age_2 = float(age_2)
                    agemean = (age_2 - age_1) / 2.0
            except:
                agemean = int(agegroup)
            self.age_means[agegroup_id] = agemean

    def distribute_kids_to_school(self):
        closest_schools = self.area.world.get_closest_schools(
            self.area, self.MAX_SCHOOLS
        )
        n_school = 0
        current_school = self.area.world.schools[closest_schools[n_school]]
        school_random_mode = False
        for person in self.area.people.values():
            while (current_school.n_pupils == current_school.n_pupils_max) and (not school_random_mode):
                n_school += 1
                if n_school == self.MAX_SCHOOLS:
                    school_random_mode = True
                else:
                    current_school = self.area.world.schools[closest_schools[n_school]]
            agemean = self.age_means[person.age]
            if agemean > current_school.age_min and agemean < current_school.age_max:
                current_school.pupils[current_school.n_pupils] = person
                person.school = current_school
                current_school.n_pupils += 1



