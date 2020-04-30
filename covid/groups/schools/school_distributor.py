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
    Distributes students to different schools
    """

    def __init__(self, schools, area):
        self.area = area
        self.world = area.world
        self.msoarea = area.msoarea
        self.schools = schools
        self.MAX_SCHOOLS = self.world.config["schools"]["neighbour_schools"]
        self.SCHOOL_AGE_RANGE = self.world.config["schools"]["school_age_range"]
        self.education_sector_label = (
            self.world.config["companies"]["key_sector"]["schools"]
        )
        self.closest_schools_by_age = {}
        self.is_agemean_full = {}
        for agegroup, school_tree in self.schools.school_trees.items():
            closest_schools = []
            closest_schools_idx = self.schools.get_closest_schools(
                agegroup, self.area, self.MAX_SCHOOLS,
            )
            for idx in closest_schools_idx:
                close_school = self.schools.members[
                    self.schools.school_agegroup_to_global_indices[agegroup][idx]
                ]
                closest_schools.append(close_school)
                self.area.schools.append(close_school)

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
                person.nomis_bin <= self.SCHOOL_AGE_RANGE[1]
                and person.nomis_bin >= self.SCHOOL_AGE_RANGE[0]
            ):  # person.nomis_bin from 5 up to 19 yo
                agegroup = self.area.world.inputs.decoder_age[person.nomis_bin]
                agemean = self.compute_age_group_mean(agegroup)
                if self.is_agemean_full[
                    agegroup
                ]:  # if all schools at that age are full, assign one randomly
                    if person.nomis_bin == 6:  # if it is 18-19 yo, then do not fill
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

    def distribute_teachers_to_school(self):
        """
        Education sector
            2311: Higher education teaching professional
            2312: Further education teaching professionals
            2314: Secondary education teaching professionals
            2315: Primary and nursery education teaching professionals
            2316: Special needs education teaching professionals
        """
        # find people working in education
        #TODO add key-company-sector id to config.yaml
        teachers = [
            person for idx,person in enumerate(self.msoarea.work_people)
            if person.industry == self.education_sector_label
        ]
        
        # equal chance to work in any school nearest to any area within msoa
        # Note: doing it this way rather then putting them into the area which
        # is currently chose in the for-loop in the world.py file ensure that
        # teachers are equally distr., no over-crowding
        areas_in_msoa = self.msoarea.oareas
        areas_rv = stats.rv_discrete(
            values=(
                np.arange(len(areas_in_msoa)),
                np.array([1/len(areas_in_msoa)]*len(areas_in_msoa))
            )
        )
        areas_rnd_arr = areas_rv.rvs(size=len(teachers))

        for i,teacher in enumerate(teachers):
            if teacher.industry_specific != None:
                area = areas_in_msoa[areas_rnd_arr[i]]
                    
                #TODO currently we make no distinction between school levels
                # because age ranges of schools are not correct
                for school in area.schools:
                    if (school.n_teachers < school.n_teachers_max):# and \
                        #(teacher.industry_specific in school.sector):
                        teacher.school = school.id
                        school.n_teachers += 1
                    #elif teacher.industry_specific is "special_needs":
                    #    # everyone has special needs :-)
                    #    #TODO fine better why for filtering
                    #    teacher.school = school.id
                    #    school.n_teachers += 1


