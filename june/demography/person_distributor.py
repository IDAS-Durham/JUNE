import logging
from collections import OrderedDict

import numpy as np
from scipy import stats

from june.demography import Person

logger = logging.getLogger(__name__)


class PersonDistributor:
    """
    Creates the population of the given area with sex and age given
    by the census statistics
    """

    def __init__(
            self,
            world,
            people,
            areas,
            area,
            msoareas,
            compsec_by_sex_df,
            workflow_df,
            key_compsec_ratio_by_sex_df,
            key_compsec_distr_by_sex_df,
            commute_gen,
    ):
        """
        """
        self.world = world
        self.areas = areas
        self.area = area
        self.msoareas = msoareas
        self.people = people
        self.STUDENT_THRESHOLD = self.world.config["people"]["student_age_group"]
        self.ADULT_THRESHOLD = self.world.config["people"]["adult_threshold"]
        self.OLD_THRESHOLD = self.world.config["people"]["old_threshold"]
        self.area.men_by_age = {}
        self.area.women_by_age = {}
        self.relevant_groups = self.world.relevant_groups
        self._get_key_compsec_id(self.world.config)
        self.no_kids_area = False
        self.no_students_area = False
        self.compsec_by_sex_df = compsec_by_sex_df
        self.workflow_df = workflow_df
        self.compsec_specic_ratio_by_sex_df = key_compsec_ratio_by_sex_df
        self.compsec_specic_distr_by_sex_df = key_compsec_distr_by_sex_df
        self.commute_gen = commute_gen
        self._init_random_variables()

    def _get_key_compsec_id(self, config):
        key_compsec = {
            key: value for key, value in config.items() if "sub_sector" in value
        }
        self.key_compsec_id = []
        for key1, value1 in key_compsec.items():
            for key2, value2 in value1.items():
                if key2 == "sector":
                    self.key_compsec_id.append(value2)

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
                    "sex must be with male or female. Intead got {person.sex}"
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

    def _assign_work_msoarea(self, i, person, msoa_man, msoa_woman):
        """
        Return: str,
            MOSA11CD area code
        """
        if person.sex == 1:
            work_msoarea_name = self.workflow_df.index.values[msoa_woman[i]]
        else:
            work_msoarea_name = self.workflow_df.index.values[msoa_man[i]]

        person.work_msoarea = work_msoarea_name

        idx = np.where(self.msoareas.names_in_order == work_msoarea_name)[0]
        if len(idx) != 0:
            self.msoareas.members[idx[0]].work_people.append(person)
        else:
            # TODO count people who work outside of the region
            # we currently simulate
            idx = np.random.choice(np.arange(len(self.msoareas.names_in_order)))
            self.msoareas.members[idx].work_people.append(person)

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
            age_1, age_2 = self._get_age_brackets(self.areas.decoder_age[nomis])
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
            person = Person(
                age=age_random,
                nomis_bin=nomis_bin,
                sex=sex_random,
                econ_index=0,
                mode_of_transport=self.commute_gen.weighted_random_choice(),
                area=self.area
            )  # self.area.regional_commute_generator.weighted_random_choice())
            # assign person to an industry TODO: implement unemployment
            if is_working_age:
                self._assign_work_msoarea(
                    i, person, work_msoa_man_rnd_array, work_msoa_woman_rnd_array,
                )
                self._assign_industry(
                    i,
                    person,
                    companysector_male_rnd_array,
                    companysector_female_rnd_array,
                )
            self.people.members.append(person)
            self.area.add(person)
            person.area = self.area
            # assign person to the right group, this is used in the household distributor.:
            if sex_random == 0:
                if age_random not in self.area.men_by_age:
                    self.area.men_by_age[age_random] = []
                self.area.men_by_age[age_random].append(person)
            else:
                if age_random not in self.area.women_by_age:
                    self.area.women_by_age[age_random] = []
                self.area.women_by_age[age_random].append(person)

        self.area.men_by_age = OrderedDict(sorted(self.area.men_by_age.items()))
        self.area.women_by_age = OrderedDict(sorted(self.area.women_by_age.items()))
        total_people = 0
        for people_dict in [self.area.men_by_age, self.area.women_by_age]:
            for age in people_dict.keys():
                total_people += len(people_dict[age])

        if total_people != self.area.n_residents:
            raise BaseException(
                f"The number of people created {total_people} does not match" / \
                " the areas' number of residents {self.area.n_residents}"
            )
