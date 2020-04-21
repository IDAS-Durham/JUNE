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

    def __init__(self, people, area, msoareas, companysector_by_sex_dict, companysector_by_sex_df, workflow_df, companysector_specific_by_sex_df):
        self.area = area
        self.msoareas = msoareas
        self.people = people
        self.STUDENT_THRESHOLD = area.world.config["people"]["student_age_group"]
        self.ADULT_THRESHOLD = area.world.config["people"]["adult_threshold"]
        self.OLD_THRESHOLD = area.world.config["people"]["old_threshold"]
        self.no_kids_area = False
        self.no_students_area = False
        self.companysector_by_sex_dict = companysector_by_sex_dict
        self.companysector_by_sex_df = companysector_by_sex_df
        self.workflow_df = workflow_df
        self.health_index = HealthIndex(self.area.world.config)
        self.companysector_specific_by_sex_df = companysector_specific_by_sex_df
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
        self.industry_dict = {
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
        distribution_male = self.companysector_by_sex_dict[self.area.name]["m"]
        self.sector_distribution_male = stats.rv_discrete(values=(numbers, distribution_male))
        distribution_female = self.companysector_by_sex_dict[self.area.name]["f"]
        self.sector_distribution_female = stats.rv_discrete(values=(numbers, distribution_female))

    def _assign_industry(self, i, sex, age, sector_man, sector_woman, employed=True):
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

        if age < self.ADULT_THRESHOLD:
            # too young to work
            return None
        elif age > self.OLD_THRESHOLD:
            # too old to work
            return None

        else:
        
            if employed == False:
                industry = "NA"
            else:
                ## accss relevant indudtry label
                if sex == 0: # Male
                    industry_id = sector_man[i]
                elif sex == 1: # Female
                    industry_id = sector_woman[i]
                else:
                    raise ValueError('sex must be with male or female. Intead got {}'.format(sex_random))
                industry = industry_dict[industry_id]

            return industry

      
    def _assign_industry_specific(self, ratio, distribution):
        MC_random = np.random.uniform()
        industry_specific_id = None

        # Check if person should be assigned any specific industry given their sector
        if MC_random < ratio:
            pass
        else:
            # Assign specific industry according to distribution
            numbers = np.arange(len(distribution))
            random_variable = stats.rv_discrete(values=(numbers,distribution))
            industry_specific_id = random_variable.rvs(size=1)
            
        return industry_specific_id
            

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
        work_msoa_woman_rnd_array = self.work_msoa_woman_rv.rvs(size=self.area.n_residents)
        companysector_male_rnd_array = self.sector_distribution_male.rvs(size=self.n_residents)
        companysector_female_rnd_array = self.sector_distribution_female.rvs(size=self.n_residents)

        # this won't work with this as this df is actually a dict - but this can be fixed
        healthcare_specific_slice = self.companysector_specific_by_sex_df[:4]
        education_specific_slice = self.companysector_specific_by_sex_df[:4]

        male_education_specific = np.sum(education_specific_slice['males'])
        male_healthcare_specific = np.sum(healthcare_specific_slice['males'])
        female_education_specific = np.sum(education_specific_slice['females'])
        female_healthcare_specific = np.sum(healthcare_specific_slice['females'])

        male_education = np.sum(self.companysector_by_sex_df['m P'])
        male_healthcare = np.sum(self.companysector_by_sex_df['m Q'])
        female_education = np.sum(self.companysector_by_sex_df['f P'])
        female_healthcare = np.sum(self.companysector_by_sex_df['f Q'])

        male_healthcare_ratio = male_healthcare_specific/male_healthcare
        male_education_ratio = male_education_specific/male_education
        female_healthcare_ratio = female_healthcare_specific/female_healthcare
        female_education_ratio = female_education_specific/female_education

        male_healthcare_distribution = np.array(healthcare_specific_slice['males'])/male_healthcare_specific
        male_education_distribution = np.array(education_specific_slice['males'])/male_education_specific
        female_healthcare_distribution = np.array(healthcare_specific_slice['females'])/female_healthcare_specific
        female_education_distribution = np.array(education_specific_slice['females'])/female_education_specific


        for i in range(0, self.area.n_residents):
            sex_random = sex_random_array[i]
            age_random = age_random_array[i]
            nomis_bin = nomis_bin_random_array[i]
            health_index = self.health_index.get_index_for_age(age_random)
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
                health_index,
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

            person.industry = self._assign_industry(
                i,
                sex_random,
                age_random,
                companysector_male_rnd_array,
                companysector_female_rnd_array)

            # assign specific industry if relevant based on sex

            if person.industry == 'Q': #Healthcare
                if sex_random == 0: # Male
                    industry_specific_id = self._assign_industry_specific(male_healthcare_ratio, male_healthcare_distribution)
                    if industry_specific_id is not None:
                        industry_specific_code = healthcare_specific_slice['occupation_codes'][industry_specific_id[0]]
                        person.industry_specific = industry_specific_code
                elif sex_random == 1: # Female
                    industry_specific_id = self._assign_industry_specific(female_healthcare_ratio, female_healthcare_distribution)
                    if industry_specific_id is not None:
                        industry_specific_code = healthcare_specific_slice['occupation_codes'][industry_specific_id[0]]
                        person.industry_specific = industry_specific_code
                else:
                    raise ValueError('sex must be with male or female. Intead got {}'.format(sex_random))
                
            elif person.industry == 'P': # Education
                if sex_random == 0: # Male 
                    industry_specific_id = self._assign_industry_specific(male_education_ratio, male_education_distribution)
                    if industry_specific_id is not None:
                        industry_specific_code = education_specific_slice['occupation_codes'][industry_specific_id[0]]
                        person.industry_specific = industry_specific_code
                elif sex_random == 1: # Female
                    industry_specific_id = self._assign_industry_specific(female_education_ratio, female_education_distribution)
                    if industry_specific_id is not None:
                        industry_specific_code = education_specific_slice['occupation_codes'][industry_specific_id[0]]
                        person.industry_specific = industry_specific_code
                else:
                    raise ValueError('sex must be with male or female. Instead got {}'.format(sex_random))
                
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
