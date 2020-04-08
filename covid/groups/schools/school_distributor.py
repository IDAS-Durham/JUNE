import numpy as np
from random import uniform
from scipy import stats
import warnings
#from covid.school import SchoolError

EARTH_RADIUS = 6371  # km

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""


class SchoolDistributor:
    """
    Distributes students to different schools
    """

    def __init__(self, schools, area):
        self.area = area
        self.schools = schools
        self.MAX_SCHOOLS = area.world.config["schools"]["neighbour_schools"]
        self.SCHOOL_AGE_RANGE = area.world.config["schools"]["school_age_range"]
        self.closest_schools_by_age = {}
        self.is_agemean_full = {}
        for agegroup, school_tree in self.schools.school_trees.items():
            closest_schools = []
            closest_schools_idx = self.schools.get_closest_schools(
                agegroup, self.area, self.MAX_SCHOOLS,
            )
            for idx in closest_schools_idx:
                closest_schools.append(
                    self.schools.members[
                        self.schools.school_agegroup_to_global_indices[agegroup][idx]
                    ]
                )
            agemean = self.compute_age_group_mean(agegroup)
            self.closest_schools_by_age[agegroup] = closest_schools
            self.is_agemean_full[agegroup] = False

    def compute_age_group_mean(self, agegroup):
        try:
            age_1, age_2 = agegroup.split("-")
            if age_2 == "XXX":
                agemean = 90
            else:
                age_1 = float(age_1)
                age_2 = float(age_2)
                agemean = (age_2 + age_1) / 2.0
        except:
            agemean = int(agegroup)
        return agemean

    def distribute_kids_to_school(self):
        for person in self.area.people:
            if (
                person.age <= self.SCHOOL_AGE_RANGE[1]
                and person.age >= self.SCHOOL_AGE_RANGE[0]
            ):  # person age from 5 up to 19 yo
                agegroup = self.area.world.decoder_age[person.age]
                agemean = self.compute_age_group_mean(agegroup)
                if self.is_agemean_full[
                    agegroup
                ]:  # if all schools at that age are full, assign one randomly
                    if person.age == 6:  # if it is 18-19 yo, then do not fill
                        continue
                    random_number = np.random.randint(0, self.MAX_SCHOOLS, size=1)[0]
                    school = self.closest_schools_by_age[agegroup][random_number]
                else:
                    schools_full = 0
                    for i in range(0, self.MAX_SCHOOLS):  # look for non full school
                        school = self.closest_schools_by_age[agegroup][i]
                        if school.n_pupils >= school.n_pupils_max:
                            schools_full += 1
                        else:
                            break
                    if schools_full == self.MAX_SCHOOLS:  # all schools are full
                        self.is_agemean_full[agegroup] = True
                        random_number = np.random.randint(0, self.MAX_SCHOOLS, size=1)[
                            0
                        ]
                        school = self.closest_schools_by_age[agegroup][random_number]
                    else:  # just keep the school saved in the previous for loop
                        pass
                school.people.append(person)
                person.school = school
                school.n_pupils += 1
