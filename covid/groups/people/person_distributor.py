import numpy as np
from scipy import stats
from covid.groups.people import Person
from covid.groups.people.health_index import HealthIndex

class PersonError(BaseException):
    pass

class PersonDistributor:
    """
    Creates the population of the given area with sex and age given
    by the census statistics
    """
    def __init__(self, people, area):
        self.area = area
        self.people = people
        self.STUDENT_THRESHOLD = area.world.config["people"]["student_age_group"]
        self.ADULT_THRESHOLD   = area.world.config["people"]["adult_threshold"]
        self.OLD_THRESHOLD     = area.world.config["people"]["old_threshold"]
        self._init_random_variables()
        self.no_kids_area      = False
        self.no_students_area  = False

    def _get_age_brackets(self, nomis_age_bin):
        try:
            age_1, age_2 = nomis_age_bin.split("-")
            if age_2 == "XXX":
                age_2 = 99
        except:
            age_1 = int(nomis_age_bin)
            age_2 = age_1
        return int(age_1), int(age_2)

    def _init_random_variables(self):
        """
        Reads the frequencies for different attributes based on the census data,
        and initializes random variables following the discrete distributions.
        """
        # age data
        age_freq = self.area.census_freq["age_freq"]
        age_kids_freq = age_freq.values[: self.ADULT_THRESHOLD]
        # check if there are no kids in the area, and if so,
        # declare it a no kids area.
        if np.sum(age_kids_freq) == 0.0:
            self.no_kids_area = True
        else:
            age_kid_freqs_norm = age_kids_freq / np.sum(age_kids_freq)
            self.area.kid_age_rv = stats.rv_discrete(
                values=(np.arange(0, self.ADULT_THRESHOLD), age_kid_freqs_norm)
            )
        #age_adults_freq = age_freq.values[self.ADULT_THRESHOLD :]
        #adult_freqs_norm = age_adults_freq / np.sum(age_adults_freq)
        #self.area.adult_age_rv = stats.rv_discrete(
        #    values=(np.arange(self.ADULT_THRESHOLD, len(age_freq)), adult_freqs_norm)
        #)
        self.area.nomis_bin_rv = stats.rv_discrete(
            values=(np.arange(0, len(age_freq)), age_freq.values)
        )
        # sex data
        sex_freq = self.area.census_freq["sex_freq"]
        self.area.sex_rv = stats.rv_discrete(
            values=(np.arange(0, len(sex_freq)), sex_freq.values)
        )

    def populate_area(self):
        """
        Creates all people living in this area, with the charactersitics
        given by the random variables declared in _init_random_variables.
        The dictionaries with the form self.area._* are meant to be used
        by the household distributor as the pool of people available to c
        create households.
        """
        self.area._kids = {}
        self.area._men = {}
        self.area._women = {}
        self.area._oldmen = {}
        self.area._oldwomen = {}
        self.area._student_keys = {}
        # create age keys for men and women TODO # this would be use to match age of couples
        # for d in [self._men, self._women, self._oldmen, self._oldwomen]:
        #    for i in range(self.ADULT_THRESHOLD, self.OLD_THRESHOLD):
        #        d[i] = {}
        nomis_bin_random_array = self.area.nomis_bin_rv.rvs(size=self.area.n_residents)
        age_random_array = []
        for nomis in nomis_bin_random_array:
            age_1, age_2 = self._get_age_brackets(self.area.world.inputs.decoder_age[nomis])
            age = np.random.randint(age_1, age_2+1, 1)[0]
            age_random_array.append(age)
        sex_random_array = self.area.sex_rv.rvs(size=self.area.n_residents)
        for i in range(0, self.area.n_residents):
            sex_random = sex_random_array[i]
            age_random = age_random_array[i]
            nomis_bin = nomis_bin_random_array[i]
            person = Person(
                self.people.total_people, self.area, age_random, nomis_bin, sex_random, 0, 0
            )
            self.people.members.append(person)
            self.area.people.append(person)
            self.people.total_people += 1
            # assign person to the right group:
            if nomis_bin < self.ADULT_THRESHOLD:
                self.area._kids[i] = person
            elif nomis_bin < self.OLD_THRESHOLD:
                if sex_random == 0:
                    self.area._men[i] = person
                else:
                    self.area._women[i] = person
                if person.nomis_bin in [6, 7]:  # that person can be a student
                    self.area._student_keys[i] = person
            else:
                if sex_random == 0:
                    self.area._oldmen[i] = person
                else:
                    self.area._oldwomen[i] = person
        try:
            assert (
                sum(
                    map(
                        len,
                        [
                            self.area._kids.keys(),
                            self.area._men.keys(),
                            self.area._women.keys(),
                            self.area._oldmen.keys(),
                            self.area._oldwomen.keys(),
                        ],
                    )
                )
                == self.area.n_residents
            )
        except:
            raise (
                "Number of men, women, oldmen, oldwomen, and kids doesnt add up to total population"
            )
