import numpy as np
from scipy import stats

from covid.groups.people import Person
from covid.groups.people.health_index import HealthIndex
from collections import OrderedDict


class PersonError(BaseException):
    pass


class PersonDistributor:
    """
    Creates the population of the given area with sex and age given
    by the census statistics
    """

    def __init__(
        self,
        timer,
        people,
        area,
        msoareas,
        compsec_by_sex_df,
        workflow_df,
        key_compsec_ratio_by_sex_df,
        key_compsec_distr_by_sex_df,
    ):
        """
        """
        self.timer = timer
        self.area = area
        self.msoareas = msoareas
        self.people = people
        self.STUDENT_THRESHOLD = area.world.config["people"]["student_age_group"]
        self.ADULT_THRESHOLD = area.world.config["people"]["adult_threshold"]
        self.OLD_THRESHOLD = area.world.config["people"]["old_threshold"]
        self.key_compsec_id = [
            value for key, value in area.world.config["companies"]["key_sector"].items()
        ]
        self.no_kids_area = False
        self.no_students_area = False
        self.area.men_by_age = {}
        self.area.women_by_age = {}
        self.compsec_by_sex_df = compsec_by_sex_df
        self.workflow_df = workflow_df
        self.health_index = HealthIndex(self.area.world.config)
        self.compsec_specic_ratio_by_sex_df = key_compsec_ratio_by_sex_df
        self.compsec_specic_distr_by_sex_df = key_compsec_distr_by_sex_df
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
        # check if there are no kids in the area, and if so,
        # declare it a no kids area.
        #self.area.nomis_bin_rv = stats.rv_discrete(
        #    values=(np.arange(0, len(age_freq)), age_freq.values)
        #)
        self.area.nomis_bin_random_values = []
        for agebin in np.arange(0, len(age_freq)):
            n_age = int(round(age_freq.iloc[agebin] * self.area.n_residents))
            for _ in range(n_age):
                self.area.nomis_bin_random_values.append(agebin)
        np.random.shuffle(self.area.nomis_bin_random_values)
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

        # companies data
        numbers = np.arange(1, 22)
        m_col = [col for col in self.compsec_by_sex_df.columns.values if "m " in col]

        distribution_male = self.compsec_by_sex_df.loc[self.area.name][m_col].values
        self.sector_distribution_male = stats.rv_discrete(
            values=(numbers, distribution_male)
        )

        f_col = [col for col in self.compsec_by_sex_df.columns.values if "f " in col]
        distribution_female = self.compsec_by_sex_df.loc[self.area.name][f_col].values
        self.sector_distribution_female = stats.rv_discrete(
            values=(numbers, distribution_female)
        )
        self.industry_dict = {
            (idx + 1): col.split(" ")[-1] for idx, col in enumerate(m_col)
        }

    def _assign_industry(self, i, person, sector_man, sector_woman, employed=True):
        """
        Note: in this script self.area.name is used and assumed to be (string) OArea code
        THIS MIGHT NEED CHANGING

        :returns: (string) letter of inductry sector
        
        Given a person's sex, their employment status, their msoarea,
        use the industry_by_sex_dict to assign each person an industry
        according to the generated probability distribution
        """

        if employed:
            # get industry label
            if person.sex == 0:  # Male
                industry_id = sector_man[i]
            elif person.sex == 1:  # Female
                industry_id = sector_woman[i]
            else:
                raise ValueError(
                    "sex must be with male or female. Intead got {}".format(sex_random)
                )
            person.industry = self.industry_dict[industry_id]

            if person.industry in self.key_compsec_id:
                self._assign_key_industry(person)
        else:
            pass

    def _assign_key_industry(self, person):
        """
        Given a person who we know is in an industry we want to be more specific
        on the job for, we assign them a specific job e.g. we want to assign
        teachers specifically, who belong to the 'Education' sector.
        The output of the function is a 4-digit number corresponding to
        the specific job - this number corresponds to the NOMIS
        annual occupation survey:

            Healthcares sector
                2211: Medical practitioners
                2217: Medical radiographers
                2231: Nurses
                2232: Midwives

            Education sector
                2311: Higher education teaching professional
                2312: Further education teaching professionals
                2314: Secondary education teaching professionals
                2315: Primary and nursery education teaching professionals
                2316: Special needs education teaching professionals
        """
        # TODO if input date is provided nicely we don't need this anymore
        # TODO this dictionary are the only key_compsec currently implemented
        key_compsec_dict = {
            2314: "secondary",
            2315: "primary",
            2316: "special_needs",
        }
        compsec_decoder = {"Q": "healthcare", "P": "education"}
        sex_decoder = {0: "male", 1: "female"}

        MC_random = np.random.uniform()

        ratio = self.compsec_specic_ratio_by_sex_df.loc[
            compsec_decoder[person.industry], sex_decoder[person.sex]
        ]
        distribution = self.compsec_specic_distr_by_sex_df.loc[
            (compsec_decoder[person.industry],), sex_decoder[person.sex]
        ].values

        # Select people working in key industries

        if MC_random < ratio:
            # print(MC_random, ratio)
            key_industry_id = None
        else:
            # Assign job category within key industry
            numbers = np.arange(len(distribution))
            random_variable = stats.rv_discrete(values=(numbers, distribution))
            key_industry_id = random_variable.rvs(size=1)
        if key_industry_id is not None:
            key_industry_code = self.compsec_specic_distr_by_sex_df.loc[
                (compsec_decoder[person.industry])
            ].index.values[key_industry_id[0]]

            if key_industry_code in key_compsec_dict.keys():
                person.industry_specific = key_compsec_dict[key_industry_code]
            else:
                person.industry_specific = key_industry_code

    def assign_work_msoarea(self, i, sex, is_working_age, msoa_man, msoa_woman):
        """
        Return: str,
            MOSA11CD area code
        """
        if is_working_age:
            workmsoa = None
        else:
            if sex == 1:
                workmsoa = self.workflow_df.index.values[msoa_woman[i]]
            else:
                workmsoa = self.workflow_df.index.values[msoa_man[i]]
        return workmsoa

    def populate_area(self):
        """
        Creates all people living in this area, with the charactersitics
        given by the random variables declared in _init_random_variables.
        The dictionaries with the form self.area._* are meant to be used
        by the household distributor as the pool of people available to c
        create households.
        """
        # create age keys for men and women TODO # this would be use to match age of couples
        # for d in [self._men, self._women, self._oldmen, self._oldwomen]:
        #    for i in range(self.ADULT_THRESHOLD, self.OLD_THRESHOLD):
        #        d[i] = {}
        #nomis_bin_random_array = self.area.nomis_bin_rv.rvs(size=self.area.n_residents)
        nomis_bin_random_array = self.area.nomis_bin_random_values
        age_random_array = []
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
        companysector_male_rnd_array = self.sector_distribution_male.rvs(
            size=self.area.n_residents
        )
        companysector_female_rnd_array = self.sector_distribution_female.rvs(
            size=self.area.n_residents
        )

        for i in range(self.area.n_residents):
            sex_random = sex_random_array[i]
            age_random = age_random_array[i]
            nomis_bin = nomis_bin_random_array[i]
            is_working_age = self.ADULT_THRESHOLD <= nomis_bin <= self.OLD_THRESHOLD
            work_msoa_rnd = self.assign_work_msoarea(
                i,
                sex_random,
                is_working_age,
                work_msoa_man_rnd_array,
                work_msoa_woman_rnd_array,
            )
            health_index = self.health_index.get_index_for_age(age_random)
            person = Person(
                self.area.world,
                self.people.total_people,
                self.area,
                work_msoa_rnd,
                age_random,
                nomis_bin,
                sex_random,
                health_index,
                0,  # economic index, not implemented yet.
                mode_of_transport=None,
            )  # self.area.regional_commute_generator.weighted_random_choice())
            # assign person to an industry TODO: implement unemployment
            if sex_random == 0:
                if age_random not in self.area.men_by_age:
                    self.area.men_by_age[age_random] = []
                self.area.men_by_age[age_random].append(person)
            else:
                if age_random not in self.area.women_by_age:
                    self.area.women_by_age[age_random] = []
                self.area.women_by_age[age_random].append(person)

            if is_working_age:
                self._assign_industry(
                    i,
                    person,
                    companysector_male_rnd_array,
                    companysector_female_rnd_array,
                )
            self.people.members.append(person)
            self.area.people.append(person)
            if nomis_bin < self.OLD_THRESHOLD:
                # find msoarea of work
                idx = np.where(self.msoareas.ids_in_order == work_msoa_rnd)[0]
                if len(idx) != 0:
                    self.msoareas.members[idx[0]].work_people.append(person)
                else:
                    # TODO count people who work outside of the region
                    # we currently simulate
                    idx = np.random.choice(np.arange(len(self.msoareas.ids_in_order)))
                    self.msoareas.members[idx].work_people.append(person)

        self.area.men_by_age = OrderedDict(sorted(self.area.men_by_age.items()))
        self.area.women_by_age = OrderedDict(sorted(self.area.women_by_age.items()))
        total_people = 0
        for people_dict in [self.area.men_by_age, self.area.women_by_age]:
            for age in people_dict.keys():
                total_people += len(people_dict[age])

        assert total_people == self.area.n_residents
