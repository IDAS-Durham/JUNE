import numpy as np
from random import uniform
from scipy import stats
import warnings
from covid.world import World
from covid.area import Area
from covid.household import Household
from covid.person import Person
from tqdm import tqdm

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""

class Distributor:
    def __init__(self, area):
        self.STUDENT_THRESHOLD = 6 
        self.ADULT_THRESHOLD = 6 # 6 corresponds to 18-19 years old
        self.OLD_THRESHOLD = 12 # 12 corresponds to 65+
        self.area = area
        self.no_kids_area = False
        self.no_students_area = False
        self._init_random_variables()
        self.residents_available = area.n_residents
        self.people_counter = 0
        self.household_counter = 0

    def _init_random_variables(self):
        """
        Reads the frequencies for different attributes based on the census data,
        and initializes random variables following the discrete distributions.
        """
        age_freq = self.area.census_freq["age_freq"]
        sex_freq = self.area.census_freq["sex_freq"]
        household_freq = self.area.census_freq["household_freq"]
        n_households = self.area.n_households
        # create a random variable with the census data to sample from it
        self.sex_rv = stats.rv_discrete(values=(np.arange(0,len(sex_freq)),sex_freq.values))
        # create random variables for adult and kids age
        age_kids_freq = age_freq.values[:self.ADULT_THRESHOLD]
        # check if there are no kids in the area
        if np.sum(age_kids_freq) == 0.0:
            self.no_kids_area = True
        else:
            age_kid_freqs_norm =  age_kids_freq / np.sum(age_kids_freq)
            self.kid_age_rv = stats.rv_discrete(values=(np.arange(0, self.ADULT_THRESHOLD), age_kid_freqs_norm))
        age_adults_freq = age_freq.values[self.ADULT_THRESHOLD:] 
        adult_freqs_norm = age_adults_freq / np.sum(age_adults_freq)
        self.adult_age_rv = stats.rv_discrete(values=(np.arange(self.ADULT_THRESHOLD, len(age_freq)), adult_freqs_norm))
        self.age_rv = stats.rv_discrete(values=(np.arange(0, len(age_freq)), age_freq.values))
        # random variable for household freq.
        self.household_rv = stats.rv_discrete(values=(np.arange(0,len(household_freq)), household_freq.values))
        self.age_groups_rv = stats.rv_discrete(values=([-1, 0, 1], [0.2, 0.6, 0.2]))
        self.same_sex_rv = stats.rv_discrete(values=([0,1], [0.9, 0.1])) # when we match sex, we assume 10% of first 2 adults have same sex.
        age_students_freq = age_freq.values[6:8]
        if np.sum(age_students_freq) == 0.0:
            self.no_student_area = True
        else:
            self.student_rv = stats.rv_discrete(values=([6,7], age_students_freq / np.sum(age_students_freq)))

    def populate_area(self):
        """
        Creates all people living in this area.
        """
        self._kids = {}
        self._men = {}
        self._women = {}
        self._oldmen = {}
        self._oldwomen = {}
        self._student_keys = {}
        # create age keys for men and women TODO
        #for d in [self._men, self._women, self._oldmen, self._oldwomen]:
        #    for i in range(self.ADULT_THRESHOLD, self.OLD_THRESHOLD):
        #        d[i] = {}
        for i in range(0, self.area.n_residents):
            age_random = self.age_rv.rvs(size=1)[0]
            sex_random = self.sex_rv.rvs(size=1)[0]
            person = Person(self.area.world.total_people,
                            self.area,
                            age_random,
                            sex_random,
                            0,
                            0)
            self.area.world.people[self.area.world.total_people] = person
            self.area.people[i] = person
            self.area.world.total_people += 1
            # assign person to the right group:
            if age_random < self.ADULT_THRESHOLD:
                self._kids[i] = person
            elif age_random < self.OLD_THRESHOLD:
                if sex_random == 0:
                    self._men[i] = person
                else:
                    self._women[i] = person
                if person.age in [6,7]: #that person can be a student
                    self._student_keys[i] = person
            else:
                if sex_random == 0:
                    self._oldmen[i] = person
                else:
                    self._oldwomen[i] = person
        try:
            assert (sum(map(len, [self._kids.keys(), self._men.keys(), self._women.keys(), self._oldmen.keys(), self._oldwomen.keys()])) == self.area.n_residents)
        except:
            raise("Number of men, women, oldmen, oldwomen, and kids doesnt add up to total population")

    def _fill_random_man(self, household, counter):
        man = self._men.popitem()
        household.residents[counter] = man[1]
        try:
            del self._student_keys[man[0]]
        except KeyError:
            pass

    def _fill_random_woman(self, household, counter):
        woman = self._women.popitem()
        household.residents[counter] = woman[1]
        try:
            del self._student_keys[woman[0]]
        except KeyError:
            pass

    def _compute_compatible_adult_age(self, first_adult_age):
        age_variation = self.age_groups_rv.rvs(size=1)[0]
        if first_adult_age == len(self.area.world.decoder_age) - 1:
            age = first_adult_age - abs(age_variation)
        elif first_adult_age == self.ADULT_THRESHOLD:
            age = first_adult_age + abs(age_variation)
        else:
            age = first_adult_age + age_variation
        return age

    def _init_person_to_household(self, age, sex, household, household_person_number):
        person = Person(self.area.world.total_people,
                        self.area,
                        age,
                        sex,
                        0,
                        0)
        person.household = household
        household.residents[household_person_number] = person
        self.area.people[self.people_counter] = person
        self.area.world.people[self.area.world.total_people] = person
        self.area.world.total_people += 1
        self.people_counter += 1
        self.residents_available -= 1
        if self.residents_available <= 0:
            return False
        else:
            return True

    def _create_student_household(self, n_students, household):
        """
        Creates a student flat, filled randomly with men and women
        between 18-24 age both inclusive.
        """
        if not self._student_keys:
            return -1 # empty house
        for i in range(0, n_students):
            if not self._student_keys:
                return household
            student_key = self._student_keys.popitem()[0]
            try: #check if man
                student = self._men.pop(student_key)
            except KeyError:
                student = self._women.pop(student_key)
            household.residents[i] = student
        return household

    def _create_oldpeople_household(self, n_old, household):
        """
        Creates a household with old people( 65+ ) living in it.
        We currently assume old people live alone or in couples.
        """
        if not self._oldmen: # no men left, just fill with women
            if not self._oldwomen:
                return -1
            else:
                household.residents[0] = self._oldwomen.popitem()[1]
                if n_old >= 2 and self._oldwomen:
                    household.residents[1] = self._oldwomen.popitem()[1]
                    if n_old == 3 and self._oldwomen:
                        household.residents[2] = self._oldwomen.popitem()[1]
                        return household
                    else:
                        return household
                else:
                    return household
        elif not self._oldwomen: # no women left, fill with men
            household.residents[0] = self._oldmen.popitem()[1]
            if n_old >= 2 and self._oldmen:
                household.residents[1] = self._oldmen.popitem()[1]
                if n_old == 3 and self._oldmen:
                    household.residents[2] = self._oldmen.popitem()[1]
                    return household
                else:
                    return household
            else:
                return household
        # here we have at least one man and at least one woman
        # n = 3 case
        if n_old == 3: # if its three people, just fill random sex
            for i in range(0, 3):
                old_sex = self.sex_rv.rvs(size=1)[0]
                if old_sex == 0 or not self._oldwomen:
                    if not self._oldmen:
                        if i == 0:
                            return -1
                        else:
                            return household
                    else:
                        household.residents[i] = self._oldmen.popitem()[1]
                elif old_sex == 1 or not self._oldmen:
                    household.residents[i] = self._oldwomen.popitem()[1]
            return household
        # n <= 2 case
        old_sex = self.sex_rv.rvs(size=1)[0]
        if old_sex == 0: # it is a man 
            household.residents[0] = self._oldmen.popitem()[1]
            if n_old == 1:
                return household
            else:
                if self._oldwomen:
                    household.residents[1] = self._oldwomen.popitem()[1]
                    return household
                elif self._oldmen:
                    household.residents[1] = self._oldmen.popitem()[1]
                    return household
                else:
                    return household
        else:
            household.residents[0] = self._oldwomen.popitem()[1]
            if n_old == 1:
                return household
            else:
                if self._oldmen:
                    household.residents[1] = self._oldmen.popitem()[1]
                    return household
                elif self._oldwomen:
                    household.residents[1] = self._oldwomen.popitem()[1]
                    return household
                else:
                    return household
        raise "error"

    def _create_singleparent_household(self, n_kids, n_students, household):
        """
        Creates single parent household. The sex of the parent
        is randomized.
        """
        counter = 0
        # add adult
        adult_sex = self.sex_rv.rvs(size=1)[0]
        if adult_sex == 0 or not self._women: # if the sex is man or there are no women left
            if not self._men: # no men left 
                return -1
            else:
                self._fill_random_man(household, counter)
                counter += 1
        elif adult_sex == 1 or not self._man:
            self._fill_random_woman(household, counter)
            counter += 1

        # add dependable kids
        if not self._kids: # no kids left
            pass 
        else:
            for i in range(0, min(n_kids, len(self._kids.keys()))):
                household.residents[counter] = self._kids.popitem()[1]
                counter += 1
        # add non dependable kids
        if n_students == 0:
            return household 
        else:
            for i in range(0, min(n_students, len(self._student_keys))):
                student_key = self._student_keys.popitem()[0]
                try:
                    student = self._men.pop(student_key)
                except KeyError:
                    student = self._women.pop(student_key)
                household.residents[counter] = student
                counter += 1
        return household
    
    def _create_twoparent_household(self, n_kids, n_students, household):
        """
        Creates two parent household. Parents are assumed to have
        the same sex, however homosexual couples are created when
        that is not possible.
        """
        counter = 0
        # first adult
        if self._men:
            self._fill_random_man(household, counter)
            counter += 1
        else:
            if not self._women:
                return -1
            else:
                self._fill_random_woman(household, counter)
                counter += 1
        # second adult
        if self._women:
            self._fill_random_woman(household, counter)
            counter += 1
        else:
            if not self._men:
                return household
            else:
                self._fill_random_man(household, counter)
                counter += 1
        # add kids
        if not self._kids: # no kids left
            pass 
        else:
            for i in range(0, min(n_kids, len(self._kids.keys()))):
                household.residents[counter] = self._kids.popitem()[1]
                counter += 1
        # add non dependable kids
        if n_students == 0:
            return household 
        else:
            for i in range(0, min(n_students, len(self._student_keys))):
                student_key = self._student_keys.popitem()[0]
                try:
                    student = self._men.pop(student_key)
                except KeyError:
                    student = self._women.pop(student_key)
                household.residents[counter] = student
                counter += 1
        return household

    def populate_household(self, household):
        household_composition_decoded = self.area.world.decoder_household_composition[household.household_composition]
        n_kids, n_students, n_adults, n_old = map(int, household_composition_decoded.split(" "))
        if n_adults == 0: # then its either student flat or old people house
            if n_kids != 0: 
                raise "There are kids in a student/old house"
            if n_students != 0 and n_old == 0:
                return self._create_student_household(n_students, household)
            elif n_students == 0 and n_old != 0:
                return self._create_oldpeople_household(n_old, household)
            else:
                raise "Household configuration not possible!"
        elif n_adults == 1: # adult living alone or monoparental family with n_kids and n_students (independent child)
            return self._create_singleparent_household(n_kids, n_students, household)
        elif n_adults == 2: # two parents family with n_kids and n_students (independent child)
            return self._create_twoparent_household(n_kids, n_students, household)
        else:
            print(n_kids)
            print(n_students)
            print(n_adults)
            print(n_old)
            raise "error adults have to be 0,1 or 2"
        
    def distribute_people_to_household(self):
        if len(self.area.people) == 0:
            self.populate_area()
        house_id = 0 
        while self._men or self._women or self._oldmen or self._oldwomen:
            #print('men: ', len(self._men))
            #print('women: ', len(self._women))
            #print('oldmen: ', len(self._oldmen))
            #print('oldwommen: ', len(self._oldwomen))
            #print(self.area.census_freq["household_freq"])
            composition_id = self.household_rv.rvs(size=1)[0]
            #print(self.area.world.decoder_household_composition[composition_id])
            household = Household(house_id, composition_id, self.area)
            household = self.populate_household(household)
            if household == -1:
                continue
            self.area.households[house_id] = household
            house_id += 1
        self.kids_left = len(self._kids)

def populate_world(world:World):
    """
    Populates all areas in the world.
    """
    print("Populating areas...")
    pbar = tqdm(total=len(world.areas.keys()))
    for area in world.areas.values():
        #print(area.name)
        distributor = Distributor(area)
        distributor.populate_area()
        distributor.distribute_people_to_household()
        pbar.update(1)
        #populate_area(area)
    print("\n")
    pbar.close()

