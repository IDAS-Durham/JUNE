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
        self.max_school_radius = 10 * EARTH_RADIUS
        pass

    def distribute_kids_to_school(self):
        closest_schools = self.area.world.get_closest_schools(
            self.area, self.max_school_radius
        )
        n_school = 0
        current_school = self.area.world.schools[closest_schools[n_school]]
        for person in self.area.people.values():
            while current_school.n_pupils == current_school.n_pupils_max:
                n_school += 1
                try:
                    current_school = self.area.world.primary_schools[
                        closest_primary_schools[n_school]
                    ]
                except IndexError:
                    raise SchoolError("Run out of nearby schools")
                except KeyError:
                    print(n_school)
                    print(closest_primary_schools)
                    raise SchoolError("whooops")
