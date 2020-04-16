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

    def __init__(self, people, area, msoareas, companysector_by_sex_df, workflow_df):
        self.area = area
        self.msoareas = msoareas
        self.people = people
        self.STUDENT_THRESHOLD = area.world.config["people"]["student_age_group"]
        self.ADULT_THRESHOLD = area.world.config["people"]["adult_threshold"]
        self.OLD_THRESHOLD = area.world.config["people"]["old_threshold"]
        self.no_kids_area = False
        self.no_students_area = False
        self.companysector_by_sex_df = companysector_by_sex_df
        self.workflow_df = workflow_df
        self._init_random_variables()

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
        Reads the frequencies for this area for different attributes based on
        the census data, and initializes random variables following
        the discrete distributions.
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
        # age_adults_freq = age_freq.values[self.ADULT_THRESHOLD :]
        # adult_freqs_norm = age_adults_freq / np.sum(age_adults_freq)
        # self.area.adult_age_rv = stats.rv_discrete(
        #    values=(np.arange(self.ADULT_THRESHOLD, len(age_freq)), adult_freqs_norm)
        # )
        self.area.nomis_bin_rv = stats.rv_discrete(
            values=(np.arange(0, len(age_freq)), age_freq.values)
        )
        # sex data
        sex_freq = self.area.census_freq["sex_freq"]
        self.area.sex_rv = stats.rv_discrete(
            values=(np.arange(0, len(sex_freq)), sex_freq.values)
        )

        # work msoa area/flow data
        self.work_msoa_woman_rv = stats.rv_discrete(
            values=(
                np.arange(0, len(self.workflow_df.index.values)),
                self.workflow_df["n_woman"].values,
            )
        )
        self.work_msoa_man_rv = stats.rv_discrete(
            values=(
                np.arange(0, len(self.workflow_df.index.values)),
                self.workflow_df["n_man"].values,
            )
        )

        # company data
        ## TODO add company data intilialisation from dict of distibutions in industry_distibutions.py

    def _assign_industry(self, sex, employed=True):
        """
        :param gender: (string) male/female
        :param employed: (bool) - for now we assume all people are employed
        Note: in this script self.area.name is used and assumed to be (string) OArea code
        THIS MIGHT NEED CHANGING

        :returns: (string) letter of inductry sector
        
        Given a person's sex, their employment status, their msoarea,
        use the industry_by_sex_dict to assign each person an industry
        according to the generated probability distribution
        """

        if employed == False:
            industry = "NA"

        else:
            # access relevant probability distribtion according to the person's sex
            if sex == "male":
                # MAY NEED TO CHANGE THE USE OF self.area TO BE CORRECT LOOKUP VALUE
                # ADD try/except statements in to allow for an area not existing (after testing though)
                # ADD industry_dict to self.area as in populate_area()
                distribution = self.companysector_by_sex_df[self.area.name]["m"]
            else:
                distribution = self.companysector_by_sex_df[self.area.name]["f"]

            # assign industries to numbers A->U = 1-> 21
            industry_dict = {
                1: "A",
                2: "B",
                3: "C",
                4: "D",
                5: "E",
                6: "F",
                7: "G",
                8: "H",
                9: "I",
                10: "J",
                11: "K",
                12: "L",
                13: "M",
                14: "N",
                15: "O",
                16: "P",
                17: "Q",
                18: "R",
                19: "S",
                20: "T",
                21: "U",
            }

            numbers = np.arange(1, 22)
            # create discrete probability distribution
            random_variable = stats.rv_discrete(values=(numbers, distribution))
            # generate sample from distribution
            industry_id = random_variable.rvs(size=1)
            # accss relevant indudtry label
            industry = industry_dict[industry_id[0]]

        return industry

    def assign_work_msoarea(self, i, sex, age, msoa_man, msoa_woman):
        """
        Return: str,
            MOSA11CD area code
        """
        if age < self.ADULT_THRESHOLD:
            # too young to work
            return None
        elif age > self.OLD_THRESHOLD:
            # too old to work
            return None
        else:
            if sex == 1:
                return self.workflow_df.index.values[msoa_woman[i]]
            else:
                return self.workflow_df.index.values[msoa_man[i]]

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
            age_1, age_2 = self._get_age_brackets(
                self.area.world.inputs.decoder_age[nomis]
            )
            age = np.random.randint(age_1, age_2 + 1, 1)[0]
            age_random_array.append(age)
        sex_random_array = self.area.sex_rv.rvs(size=self.area.n_residents)
        work_msoa_man_rnd_array = self.work_msoa_man_rv.rvs(size=self.area.n_residents)
        work_msoa_woman_rnd_array = self.work_msoa_woman_rv.rvs(
            size=self.area.n_residents
        )
        for i in range(0, self.area.n_residents):
            sex_random = sex_random_array[i]
            age_random = age_random_array[i]
            nomis_bin = nomis_bin_random_array[i]
            work_msoa_rnd = self.assign_work_msoarea(
                i,
                sex_random,
                age_random,
                work_msoa_man_rnd_array,
                work_msoa_woman_rnd_array,
            )
            person = Person(
                self.people.total_people,
                self.area,
                work_msoa_rnd,
                age_random,
                nomis_bin,
                sex_random,
                0,
                0,
            )
            self.people.members.append(person)
            self.area.people.append(person)
            self.people.total_people += 1
            # assign person to the right group:
            if nomis_bin < self.ADULT_THRESHOLD:
                self.area._kids[i] = person
            elif nomis_bin < self.OLD_THRESHOLD:
                idx = np.where(self.msoareas.ids_in_order == work_msoa_rnd)[0]
                if len(idx) != 0:
                    self.msoareas.members[idx[0]].work_people.append(person)
                else:
                    # TODO count people who work outside of the region
                    # we currently simulate
                    pass
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
            # assign person to an industry
            # add some conditions to allow for employed != True - wither age and/or from a database
            person.industry = self._assign_industry(sex=sex_random)

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
