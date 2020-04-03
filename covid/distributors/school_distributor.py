import numpy as np
from random import uniform
from scipy import stats
import warnings

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
        self.PRIMARY_SCHOOL_AGE = [1, 2] # 5-9 years old, it should be until 11, we add 2/5 of category 3
        self.SECONDARY_SCHOOL_AGE = [4, 5] # 5-9 years old, it should be from 12, we add 3/5 of category 3
        self.age_group_3_rv = stats.rv_discrete(values=([0,1], [2./5., 3./5.]))
        self.area = area
        pass

    def distribute_kids_to_primary_school(self):
        closest_primary_schools = self.area.world.get_closest_primary_schools(self.area, k=500)
        n_school = 0
        current_school = self.area.world.primary_schools[closest_primary_schools[n_school]]
        for person in self.area.people.values():
            while current_school.n_pupils == current_school.n_pupils_max:
                n_school += 1
                try:
                    current_school = self.area.world.primary_schools[closest_primary_schools[n_school]]
                except IndexError:
                    raise SchoolError("Run out of nearby schools")
                except KeyError:
                    print(n_school)
                    print(closest_primary_schools)
                    raise SchoolError("whooops")

            if person.age in self.PRIMARY_SCHOOL_AGE: 
                person.school = current_school
                current_school.pupils[current_school.n_pupils] = person
                current_school.n_pupils += 1
            elif person.age == 3:
                age3_rv = self.age_group_3_rv.rvs(size=1)
                if age3_rv == 0:
                    person.school = current_school
                    current_school.pupils[current_school.n_pupils] = person
                    current_school.n_pupils += 1
            else:
                continue

    def distribute_kids_to_secondary_school(self):
        closest_secondary_schools = self.area.world.get_closest_secondary_schools(self.area, k=500)
        n_school = 0
        current_school = self.area.world.secondary_schools[closest_secondary_schools[n_school]]
        for person in self.area.people.values():
            while current_school.n_pupils == current_school.n_pupils_max:
                n_school += 1
                try:
                    current_school = self.area.world.secondary_schools[closest_secondary_schools[n_school]]
                except IndexError:
                    raise SchoolError("Run out of nearby schools")
                except KeyError:
                    print(n_school)
                    print(closest_secondary_schools)
                    raise SchoolError("whooops")

            if person.age in self.SECONDARY_SCHOOL_AGE: 
                person.school = current_school
                current_school.pupils[current_school.n_pupils] = person
                current_school.n_pupils += 1
            elif person.age == 3:
                age3_rv = self.age_group_3_rv.rvs(size=1)
                if age3_rv == 1: 
                    person.school = current_school
                    current_school.pupils[current_school.n_pupils] = person
                    current_school.n_pupils += 1
            else:
                continue












