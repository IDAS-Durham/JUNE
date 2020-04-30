import numpy as np
from random import uniform
from scipy import stats
import warnings

# from covid.school import SchoolError

EARTH_RADIUS = 6371  # km

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""


class SchoolDistributor:
    """
    Distributes students in an area to different schools 
    """

    def __init__(self, schools, area, config):
        self.area = area
        self.schools = schools
        self.MAX_SCHOOLS = config["schools"]["neighbour_schools"]
        self.SCHOOL_AGE_RANGE = config["schools"]["school_age_range"]
        self.MANDATORY_SCHOOL_AGE_RANGE = config["schools"][
            "school_mandatory_age_range"
        ]
        self.closest_schools_by_age = {}
        self.is_shool_full = {}
        for agegroup, school_tree in self.schools.school_trees.items():
            closest_schools = []
            closest_schools_idx = self.schools.get_closest_schools(
                agegroup, self.area.coordinates, self.MAX_SCHOOLS,
            )
            for idx in closest_schools_idx:
                closest_schools.append(
                    self.schools.members[
                        self.schools.school_agegroup_to_global_indices[agegroup][idx]
                    ]
                )
            self.closest_schools_by_age[agegroup] = closest_schools
            self.is_school_full[agegroup] = False

    @classmethod
    def load_from_file(cls, schools, area, config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        return SchoolDistributor(schools, area, config)

    def distribute_kids_to_school(self):
        for person in self.area.people:
            if (
                person.age <= self.SCHOOL_AGE_RANGE[1]
                and person.age >= self.SCHOOL_AGE_RANGE[0]
            ):
                if self.is_school_full[agegroup]:
                    # if it is younger than 4 or older than 18, do not fill
                    # (not necessarily everyone that age goes to school
                    if (
                        person.age <= self.MANDATORY_SCHOOL_AGE_RANGE[0]
                        or person.age > self.MANDATORY_SCHOOL_AGE_RANGE[1]
                    ):
                        continue
                    # if in mandatory age range, assign a full school randomly
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
                        self.is_school_full[agegroup] = True
                        random_number = np.random.randint(0, self.MAX_SCHOOLS, size=1)[
                            0
                        ]
                        school = self.closest_schools_by_age[agegroup][random_number]
                    else:  # just keep the school saved in the previous for loop
                        pass
                school.people.append(person)
                person.school = school
                school.n_pupils += 1
