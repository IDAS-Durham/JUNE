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
        self.MAX_SCHOOLS = 5
        self.closest_schools_by_age = {}
        self.is_agemean_full = {}
        for agemean, school_tree in self.area.world.school_trees.pairs():
            closest_schools = self.area.world.get_closest_schools(
                    agemean, self.area, self.MAX_SCHOOLS,
                    )
            self.closest_schools_by_age[agemean] = closest_schools
            self.is_agemean_full[agemean] = False

    def compute_age_group_mean(self, age):
        agegroup = self.area.world.decoder_age[age]
        try:
            age_1, age_2 = agegroup.split("-")
            if age_2 == 'XXX':
                agemean = 90
            else:
                age_1 = float(age_1)
                age_2 = float(age_2)
                agemean = (age_2 + age_1) / 2.0
        except:
            agemean = int(agegroup)
        return agemean

    def distribute_kids_to_school(self):
        for person in self.area.people.values():
            if person.age <= 6: #person age up to 19 yo
                agemean = self.compute_age_group_mean(person.age) 
                if self.is_agemean_full[agemean]: #if all schools at that age are full, assign one randomly
                    if person.age == 6: # if it has 18-19 years old, then do not fill
                        continue
                    random_number = np.random.randint(0, self.MAX_SCHOOLS, size=1)
                    school_id = self.closest_schools_by_age[agemean][random_number]
                    school = self.world.schools[agemean][school_id]
                else:
                    schools_full = 0
                    for i in range(0, self.MAX_SCHOOLS): # look for non full school
                        school_id = self.closest_schools_by_age[agemean][i]
                        school = self.world.schools[agemean][school_id]
                        if school.n_pupils >= school.n_pupils_max:
                            schools_full += 1
                        else:
                            break
                    if schools_full == self.MAX_SCHOOLS: #all schools are full
                        self.is_agemean_full[agemean] = True
                        random_number = np.random.randint(0, self.MAX_SCHOOLS, size=1)
                        school_id = self.closest_schools_by_age[agemean][random_number]
                        school = self.world.schools[agemean][school_id]
                    else: # just keep the school saved in the previous for loop
                        pass
                school.pupils[school.n_pupils] = person
                person.school = current_school
                school.n_pupils += 1
