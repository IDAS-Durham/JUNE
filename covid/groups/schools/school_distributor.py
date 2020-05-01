import numpy as np
from random import uniform
from scipy import stats
import yaml
import warnings
from typing import List, Tuple, Dict

# from covid.school import SchoolError

EARTH_RADIUS = 6371  # km


class SchoolDistributor:
    """
    Distributes students in an area to different schools 
    """

    def __init__(self, schools: "Schools", area: "Area", config: dict):
        """
        Get closest schools to this output area, per age group
        (different schools admit pupils with different age ranges)

        Parameters
        ----------
        schools: 
            instance of Schools, with information on all schools in world.
        area:
            instance of Area.
        config:
            config dictionary.
        """
        self.area = area
        self.world = area.world
        self.msoarea = area.msoarea
        self.schools = schools
        self.MAX_SCHOOLS = config["neighbour_schools"]
        self.SCHOOL_AGE_RANGE = config["school_age_range"]
        self.MANDATORY_SCHOOL_AGE_RANGE = config["school_mandatory_age_range"]
        self.education_sector_label = (
            self.world.config["companies"]["key_sector"]["schools"]
        )
        self.closest_schools_by_age = {}
        self.is_school_full = {}
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
    def from_file(
        cls, schools: "Schools", area: "Area", config_filename: str
    ) -> "SchoolDistributor":
        """
        Initialize SchoolDistributor from path to its config file 

        Parameters
        ----------
        schools: 
            instance of Schools, with information on all schools in world.
        area:
            instance of Area.
        config:
            path to config dictionary

        Returns
        -------
        SchoolDistributor instance
        """

        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        return SchoolDistributor(schools, area, config)

    def distribute_kids_to_school(self):
        """
        Function to distribute kids to schools according to distance 
        """
        self.distribute_mandatory_kids_to_school()
        self.distribute_non_mandatory_kids_to_school()

    def distribute_mandatory_kids_to_school(self):
        """
        Send kids to the nearest school among the self.MAX_SCHOOLS schools,
        that has vacancies. If none of them has vacancies, pick one of them
        at random (making it larger than it should be)
        """

        for person in self.area.people:
            if (
                person.age <= self.MANDATORY_SCHOOL_AGE_RANGE[1]
                and person.age >= self.MANDATORY_SCHOOL_AGE_RANGE[0]
            ):
                if self.is_school_full[person.age]:
                    random_number = np.random.randint(0, self.MAX_SCHOOLS, size=1)[0]
                    school = self.closest_schools_by_age[person.age][random_number]
                else:
                    schools_full = 0
                    for i in range(0, self.MAX_SCHOOLS):  # look for non full school
                        school = self.closest_schools_by_age[person.age][i]
                        if school.n_pupils >= school.n_pupils_max:
                            schools_full += 1
                        else:
                            break

                        self.is_school_full[person.age] = True
                        random_number = np.random.randint(0, self.MAX_SCHOOLS, size=1)[
                            0
                        ]
                        school = self.closest_schools_by_age[person.age][random_number]
                    else:  # just keep the school saved in the previous for loop
                        pass
                school.people.append(person)
                person.school = school
                school.n_pupils += 1

    def distribute_non_mandatory_kids_to_school(self):
        """
        For kids in age ranges that might go to school, but it is not mandatory
        send them to the closest school that has vacancies among the self.MAX_SCHOOLS closests.
        If none of them has vacancies do not send them to school
        """
        for person in self.area.people:
            if (
                self.SCHOOL_AGE_RANGE[0]
                < person.age
                < self.MANDATORY_SCHOOL_AGE_RANGE[0]
                or self.MANDATORY_SCHOOL_AGE_RANGE[1]
                < person.age
                < self.SCHOOL_AGE_RANGE[1]
            ):
                if self.is_school_full[person.age]:
                    continue
                else:
                    schools_full = 0
                    for i in range(0, self.MAX_SCHOOLS):  # look for non full school
                        school = self.closest_schools_by_age[person.age][i]
                        # check number of students in that age group
                        n_pupils_age = len(
                            [
                                pupil.age
                                for pupil in school.people
                                if pupil.age == person.age
                            ]
                        )
                        if school.n_pupils >= school.n_pupils_max or n_pupils_age >= (
                            school.n_pupils_max / (school.age_max - school.age_min)
                        ):
                            schools_full += 1
                        else:
                            break
                    if schools_full == self.MAX_SCHOOLS:  # all schools are full
                        continue

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
                    
                for school in area.schools:
                    if (teacher.industry_specific in school.sector):
                        #(school.n_teachers < school.n_teachers_max) and \
                        teacher.school = school.id
                        school.n_teachers += 1
                    elif teacher.industry_specific is "special_needs":
                        # everyone has special needs :-)
                        #TODO fine better why for filtering
                        teacher.school = school.id
                        school.n_teachers += 1


