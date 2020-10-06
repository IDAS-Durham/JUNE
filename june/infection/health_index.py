import numpy as np
import pandas as pd
import yaml
from scipy import interpolate
from june.infection.symptom_tag import SymptomTag
from june import paths
from june.utils.parse_probabilities import parse_age_probabilities
from typing import Optional, List

default_icu_hosp_filename = paths.configs_path / "defaults/ICU_hosp.dat"
default_death_hosp_filename = paths.configs_path / "defaults/Death_hosp.dat"
default_hosp_cases_filename = paths.configs_path / "defaults/cases_hosp.dat"


RKIdata = [
    [0.0, 4.0 / 100.0],
    [5.0, 4.0 / 100.0],
    [15.0, 1.5 / 100.0],
    [35.0, 4.0 / 100.0],
    [60.0, 14.0 / 100.0],
    [80.0, 46.0 / 100.0],
]

# Taken from ICNARC report
survival_rate_icu = [
    [0, 1.0],  # No death in icu reported.
    [16, 78.6 / 100.0],
    [40, 74.4 / 100.0],
    [50, 59.3 / 100.0],
    [60, 44.3 / 100.0],
    [70, 32.9 / 100.0],
    [80, 35.0 / 100.0],
]


# excess detahs
# https://www.gov.uk/government/publications/covid-19-review-of-disparities-in-risks-and-outcomes
excess_deaths = [
    [0, 1.0, 1.0],  # No death in icu reported.
    [15, 1.0, 1.0],
    [45, 79.8 / 100.0, 81.2 / 100.0],
    [64, 83.3 / 100.0, 83.7 / 100.0],
    [75, 81.8 / 100.0, 84.7 / 100.0],
    [85, 63.6 / 100.0, 75.1 / 100.0],
]


class HealthIndexGenerator:
    """
    Computes probabilities for (asymptomatic, mild symptoms, severe symptoms, 
    hospitalisation, intensive care, fatality), using the age and sex of the subject.
    The probablities of hospitalisation,death and ICU are taken taken from fits made by 
    Miguel Icaza to the England data taken from several sources.
    We will assume that the symptomatic cases that do not need hospitalisation have either 
    mild symptoms or penumonia-like symptoms the percentage of those are distrubuted 
    according to the ratios in the RKI publication (table 1/column 2 of
    https://www.rki.de/DE/Content/Infekt/EpidBull/Archiv/2020/Ausgaben/17_20.pdf?__blob=publicationFile)
    """

    def __init__(
        self,
        hosp_cases: dict,
        icu_hosp: dict,
        death_hosp: dict,
        asymptomatic_ratio=0.2,
        comorbidity_multipliers: Optional[dict] = None,
        prevalence_reference_population: Optional[dict] = None,
        male_care_home_ratios: Optional[List] = None,
        female_care_home_ratios: Optional[List] = None,
    ):
        """
        Parameters:
        - poli_hosp,poli_icu,poli_deaths:
          Each of this arrays contains 2 lists of 4 elements. 
          The first element of the list correpdons to males and the second to females.
          The elements are the indexes C,C1,C2,C3
          of the polynomial fit defined to be the probability of being hospitalised, 
          sent to an ICU unit or dying 
        - the probaility (P) is computed as 
          P=10**(C+C1*Age+C2*Age**2+C3*Age**3)
          The 10 exponent is requiered as the fits where done in logarithmic space.
        - asimpto_ratio:
          The percentage of the population that will be asymptomatic, we fixed it to 
          43% and assume that is age-independent.  This assumptions comes from 
          Vo et al 2019 ( https://doi.org/10.1101/2020.04.17.20053157 ).
          
        """
        self.hosp_cases = hosp_cases
        self.icu_hosp = icu_hosp
        self.death_hosp = death_hosp
        self.asymptomatic_ratio = asymptomatic_ratio
        self.female_care_home_ratios = female_care_home_ratios
        self.male_care_home_ratios = male_care_home_ratios
        self.make_list()
        if comorbidity_multipliers is not None:
            self.max_mild_symptom_tag = [
                tag.value for tag in SymptomTag if tag.name == "severe"
            ][0]
            self.comorbidity_multipliers = comorbidity_multipliers
            parsed_prevalence_reference_population = {}
            for comorbidity in prevalence_reference_population.keys():
                parsed_prevalence_reference_population[comorbidity] = {
                    "f": parse_age_probabilities(
                        prevalence_reference_population[comorbidity]["f"]
                    ),
                    "m": parse_age_probabilities(
                        prevalence_reference_population[comorbidity]["m"]
                    ),
                }

            self.prevalence_reference_population = (
                parsed_prevalence_reference_population
            )

    @classmethod
    def from_file(
        cls,
        hosp_filename: str = default_hosp_cases_filename,
        icu_filename: str = default_icu_hosp_filename,
        death_filename: str = default_death_hosp_filename,
        asymptomatic_ratio=0.2,
        comorbidity_multipliers=None,
        prevalence_reference_population=None,
        care_home_ratios_filename: Optional[str] =None,
    ) -> "HealthIndexGenerator":
        """
        Initialize the Health index from path to data frame, and path to config file 
        Parameters:
        - filename:
            polinome_filename:  path to the file where the coefficients of the fits to 
            the spanish data are stored.       
        Returns:
          Interaction instance
        """

        age = np.arange(0, 121, 1)

        hosp_data = np.loadtxt(hosp_filename, skiprows=1)
        age_hosp = hosp_data[:, 0]
        female_hosp = hosp_data[:, 1]
        male_hosp = hosp_data[:, 2]

        interp_female_hosp = interpolate.interp1d(
            age_hosp, female_hosp, bounds_error=False, fill_value=female_hosp[-1]
        )
        interp_male_hosp = interpolate.interp1d(
            age_hosp, male_hosp, bounds_error=False, fill_value=male_hosp[-1]
        )

        hosp_cases = [interp_female_hosp(age), interp_male_hosp(age)]

        icu_data = np.loadtxt(icu_filename, skiprows=1)
        age_icu = icu_data[:, 0]
        female_icu = icu_data[:, 1]
        male_icu = icu_data[:, 2]

        interp_female_icu = interpolate.interp1d(
            age_icu, female_icu, bounds_error=False, fill_value=female_icu[-1]
        )
        interp_male_icu = interpolate.interp1d(
            age_icu, male_icu, bounds_error=False, fill_value=male_icu[-1]
        )
        icu_hosp = [interp_female_icu(age), interp_male_icu(age)]

        death_data = np.loadtxt(death_filename, skiprows=1)
        age_death = death_data[:, 0]
        female_death = death_data[:, 1]
        male_death = death_data[:, 2]

        interp_female_death = interpolate.interp1d(
            age_death, female_death, bounds_error=False, fill_value=female_death[-1]
        )
        interp_male_death = interpolate.interp1d(
            age_death, male_death, bounds_error=False, fill_value=male_death[-1]
        )
        death_hosp = [interp_female_death(age), interp_male_death(age)]
        if care_home_ratios_filename is not None:
            with open(care_home_ratios_filename) as f:
                care_home_ratios = yaml.load(f, Loader=yaml.FullLoader)
            male_care_home_ratios = care_home_ratios['male']
            female_care_home_ratios = care_home_ratios['female']
        else:
            male_care_home_ratios = None
            female_care_home_ratios = None
        return cls(
            hosp_cases,
            icu_hosp,
            death_hosp,
            asymptomatic_ratio,
            comorbidity_multipliers=comorbidity_multipliers,
            prevalence_reference_population=prevalence_reference_population,
            male_care_home_ratios=male_care_home_ratios,
            female_care_home_ratios=female_care_home_ratios,
        )

    @classmethod
    def from_file_with_comorbidities(
        cls,
        multipliers_path: str,
        male_prevalence_path: str,
        female_prevalence_path: str,
        hosp_filename: str = default_hosp_cases_filename,
        icu_filename: str = default_icu_hosp_filename,
        death_filename: str = default_death_hosp_filename,
        asymptomatic_ratio: float = 0.2,
    ) -> "HealthIndexGenerator":
        """
        Initialize the Health index from path to data frame, and path to config file 
        Parameters:
        - filename:
            polinome_filename:  path to the file where the coefficients of the fits to 
            the spanish data are stored.       
        Returns:
          Interaction instance
        """
        with open(multipliers_path) as f:
            comorbidity_multipliers = yaml.load(f, Loader=yaml.FullLoader)
        female_prevalence = read_comorbidity_csv(female_prevalence_path)
        male_prevalence = read_comorbidity_csv(male_prevalence_path)
        prevalence_reference_population = convert_comorbidities_prevalence_to_dict(
            female_prevalence, male_prevalence
        )
        return cls.from_file(
            hosp_filename=hosp_filename,
            icu_filename=icu_filename,
            death_filename=death_filename,
            asymptomatic_ratio=asymptomatic_ratio,
            comorbidity_multipliers=comorbidity_multipliers,
            prevalence_reference_population=prevalence_reference_population,
        )

    def make_list(self):
        """
        Computes the probability of having all 7 posible outcomes for all ages between 0 and 120. 
        And for male and female 
        
        Retruns:
             3D matrix of dimensions 2 X 120 X 7. With all the probabilities of all 6 
             outcomes for 120 ages and the 2 sex.
             
             For each gender and age there are 7 numbers to define: [N_1,N_2,N3,N4,N_5,N_6,N_7].
             The idea is to select a random number, r, between 0 and 1. Depending on how this random 
             number compares with our 7 numbers, different outcomes will happen
             - if  0<r<N_1  Asymptomatic
             - if  N_1<r<N_2 Mild symptoms
             - if  N_2<r<N_3  Stays at home with pneoumonia symptoms and survives.
             - if  N_3<r<N_4  Goes to the hospital but not to ICU and survives.
             - if  N_4<r<N_5  Goes to ICU ans survives.
             - if  N_5<r<N_6  Stays at home with severe and dies.
             - if  N_6<r<N_7  Goes to the hospital but not to ICU and dies.
             - if  N_7<r<1    Goes to ICU and dies.
              
        """
        ages = np.arange(0, 121, 1)  # from 0 to 120
        self.prob_lists = np.zeros([2, 121, 7])
        self.prob_lists[:, :, 0] = self.asymptomatic_ratio
        # hosp,ICU,death ratios

        ratio_hosp_cases_female = self.hosp_cases[0]  # hospital/cases rate
        ratio_icu_hosp_female = self.icu_hosp[0]  # ICU/hosp rate
        ratio_death_hosp_female = self.death_hosp[0]  # deaths in hosp/hosp rate

        ratio_hosp_cases_male = self.hosp_cases[1]  # hospital/cases rate
        ratio_icu_hosp_male = self.icu_hosp[1]  # ICU/hosp rate
        ratio_death_hosp_male = self.death_hosp[1]  # deaths in hosp/hosp rate

        # Going to the hospital but not to ICU/hosp
        hosp_noicu_female = 1.0 - ratio_icu_hosp_female
        hosp_noicu_male = 1.0 - ratio_icu_hosp_male

        # Probability of being simptomatic but not going to hospital
        no_hosp_female = 1.0 - self.asymptomatic_ratio - ratio_hosp_cases_female
        no_hosp_male = 1.0 - self.asymptomatic_ratio - ratio_hosp_cases_male

        # Probability of getting severe
        prob_severe = np.ones(121)
        for severe_index in range(len(RKIdata) - 1):
            boolean = (RKIdata[severe_index][0] <= np.arange(0, 121, 1)) & (
                np.arange(0, 121, 1) < RKIdata[severe_index + 1][0]
            )
            prob_severe[boolean] = RKIdata[severe_index][1]
        prob_severe[prob_severe == 1] = RKIdata[len(RKIdata) - 1][1]

        # probavility of  mild simptoms
        self.prob_lists[0, :, 1] = no_hosp_female * (1 - prob_severe)
        self.prob_lists[1, :, 1] = no_hosp_male * (1 - prob_severe)

        # probavility of Surviving ICU
        survival_icu = np.ones(121)
        for survival_icu_index in range(len(survival_rate_icu) - 1):
            boolean = (
                survival_rate_icu[survival_icu_index][0] <= np.arange(0, 121, 1)
            ) & (np.arange(0, 121, 1) < survival_rate_icu[survival_icu_index + 1][0])
            survival_icu[boolean] = survival_rate_icu[survival_icu_index][1]
        survival_icu[np.arange(0, 121, 1) >= 80] = survival_rate_icu[
            len(survival_rate_icu) - 1
        ][1]

        self.prob_lists[0, :, 4] = (
            ratio_hosp_cases_female * ratio_icu_hosp_female
        ) * survival_icu  # computes icu_survivors/cases
        self.prob_lists[1, :, 4] = (
            ratio_hosp_cases_male * ratio_icu_hosp_male
        ) * survival_icu

        # probavility of Dying in icu
        icu_deaths_female = ratio_icu_hosp_female * (1 - survival_icu)
        icu_deaths_male = ratio_icu_hosp_male * (1 - survival_icu)

        # probability of Survinving  hospital

        deaths_hosp_noicu_female = (
            ratio_death_hosp_female - icu_deaths_female
        )  # deaths in hospital but not in icu/hosp
        deaths_hosp_noicu_male = ratio_death_hosp_male - icu_deaths_male

        # If the death rate in icu is around the number of deaths virtually everyone in that age dies in icu.
        deaths_hosp_noicu_female[deaths_hosp_noicu_female < 0] = 1e-3
        deaths_hosp_noicu_male[deaths_hosp_noicu_male < 0] = 1e-3

        self.prob_lists[0, :, 3] = (
            hosp_noicu_female - deaths_hosp_noicu_female
        ) * ratio_hosp_cases_female  # surviving hosp outside of icu/cases
        self.prob_lists[1, :, 3] = (
            hosp_noicu_male - deaths_hosp_noicu_male
        ) * ratio_hosp_cases_male

        # probability of dying in hospital Without icu
        self.prob_lists[0, :, 6] = deaths_hosp_noicu_female * ratio_hosp_cases_female
        self.prob_lists[1, :, 6] = deaths_hosp_noicu_male * ratio_hosp_cases_male
        """
        probability of dying in your home is the same as the number of deths above the mean of previous years
        that do not have covid 19 in the death certificate it is 23% according to 
        https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/889861/disparities_review.pdf
        """
        # excesss deaths
        excess_death_female = np.ones(121)
        excess_death_male = np.ones(121)
        for excess_deaths_index in range(len(excess_deaths) - 1):
            boolean = (
                excess_deaths[excess_deaths_index][0] <= np.arange(0, 121, 1)
            ) & (np.arange(0, 121, 1) < excess_deaths[excess_deaths_index + 1][0])
            excess_death_female[boolean] = excess_deaths[excess_deaths_index][1]
            excess_death_male[boolean] = excess_deaths[excess_deaths_index][2]

        excess_death_female[ages >= excess_deaths[-1][0]] = excess_deaths[-1][1]
        excess_death_male[ages >= excess_deaths[-1][0]] = excess_deaths[-1][2]

        deaths_at_home_female = (ratio_death_hosp_female * ratio_hosp_cases_female) * (
            1 - excess_death_female
        )
        deaths_at_home_male = (ratio_death_hosp_male * ratio_hosp_cases_male) * (
            1 - excess_death_male
        )

        self.prob_lists[0, :, 5] = deaths_at_home_female
        self.prob_lists[1, :, 5] = deaths_at_home_male

        # Probability of having sever simptoms at home but surviving

        prob_home_severe_female = no_hosp_female * prob_severe
        prob_home_severe_male = no_hosp_male * prob_severe

        self.prob_lists[0, :, 2] = prob_home_severe_female - deaths_at_home_female
        self.prob_lists[1, :, 2] = prob_home_severe_male - deaths_at_home_male

    def __call__(self, person):
        """
        Computes the probability of having all 8 posible outcomes for all ages between 0 and 120. 
        And for male and female 
        
        Retruns:
             3D matrix of dimensions 2 X 120 X 7. With all the probabilities of all 8 
             outcomes for 120 ages and the 2 sex (last outcome inferred from 1-sum(probabilities)).
        """
        if person.sex == "m":
            sex = 1
        else:
            sex = 0
        round_age = int(round(person.age))
        probabilities = self.prob_lists[sex][round_age]
        if self.male_care_home_ratios is not None and self.female_care_home_ratios is not None:
            probabilities = self.adjust_hospitalisation(
                probabilities, person, 
                male_care_home_ratio=self.male_care_home_ratios,
                female_care_home_ratio=self.female_care_home_ratios,
            )
        if hasattr(self, "comorbidity_multipliers") and person.comorbidity is not None:
            probabilities = self.adjust_for_comorbidities(
                probabilities, person.comorbidity, person.age, person.sex
            )
        return np.cumsum(probabilities)

    def adjust_hospitalisation(self, probabilities, person, male_care_home_ratio,
            female_care_home_ratio):
        if (
            person.age > 65
            and person.residence is not None
            and person.residence.group.spec != "care_home"
        ):
            # 10% of the deaths were of care home residents in realitiy, thus
            # the factor 0.9
            if person.sex == 'm':
                correction_factor = 0.9 / (1 - male_care_home_ratio[person.age])
            elif person.sex == 'f':
                correction_factor = 0.9 / (1 - female_care_home_ratio[person.age])
            last_probability = 1 - sum(probabilities)
            probabilities[[3, 4, 6]] *= correction_factor
            last_probability *= correction_factor
            probabilities[:3] *= (1 - sum(probabilities[3:]) - last_probability) / sum(
                probabilities[:3]
            )
        return probabilities

    def get_multiplier_from_reference_prevalence(self, age: int, sex: str) -> float:
        """
        Compute mean comorbidity multiplier given the prevalence of the different comorbidities
        in the reference population (for example the UK). It will be used to remove effect of comorbidities
        in the reference population
        Parameters
        ----------
        prevalence_reference_population:
            nested dictionary with prevalence of comorbidity by comorbodity, age and sex cohort
        age:
            age group to compute average multiplier
        sex:
            sex group to compute average multiplier
        Returns
        -------
            weighted_multiplier:
                weighted mean of the multipliers given prevalence
        """
        weighted_multiplier = 0.0
        for comorbidity in self.prevalence_reference_population.keys():
            weighted_multiplier += (
                self.comorbidity_multipliers[comorbidity]
                * self.prevalence_reference_population[comorbidity][sex][age]
            )
        return weighted_multiplier

    def adjust_for_comorbidities(
        self, probabilities: list, comorbidity: str, age: int, sex: str
    ):
        """
        Compute adjusted probabilities for a person with given comorbidity, age and sex.
        Parameters
        ----------
        probabilities:
            list with probability values for the 8 different outcomes (has len 7, but 8th value
            can be inferred from 1 - probabilities.sum())
        comorbidity:
            comorbidty type that the person has
        age:
            age group to compute average multiplier
        sex:
            sex group to compute average multiplier
        Returns
        -------
            probabilities adjusted for comorbidity 
        """

        multiplier = self.comorbidity_multipliers.get(comorbidity, 1.0)
        reference_weighted_multiplier = self.get_multiplier_from_reference_prevalence(
            age=age, sex=sex
        )
        effective_multiplier = multiplier / reference_weighted_multiplier
        return self.adjust_probabilities_for_comorbidities(
            probabilities, effective_multiplier
        )

    def adjust_probabilities_for_comorbidities(
        self, probabilities, effective_multiplier
    ):
        """
        Compute adjusted probabilities given an effective multiplier
        Parameters
        ----------
        probabilities:
            list with probability values for the 8 different outcomes (has len 7, but 8th value
            can be inferred from 1 - probabilities.sum())
        effective_multiplier:
            factor that amplifies severe outcomes
        Returns
        -------
            adjusted probabilities
        """

        probabilities_with_comorbidity = np.zeros_like(probabilities)
        p_mild = probabilities[: self.max_mild_symptom_tag].sum()
        p_severe = probabilities[self.max_mild_symptom_tag :].sum() + (
            1 - probabilities.sum()
        )
        p_severe_with_comorbidity = p_severe * effective_multiplier
        p_mild_with_comorbidity = 1 - p_severe_with_comorbidity
        probabilities_with_comorbidity[: self.max_mild_symptom_tag] = (
            probabilities[: self.max_mild_symptom_tag]
            * p_mild_with_comorbidity
            / p_mild
        )
        probabilities_with_comorbidity[self.max_mild_symptom_tag :] = (
            probabilities[self.max_mild_symptom_tag :]
            * p_severe_with_comorbidity
            / p_severe
        )
        return probabilities_with_comorbidity


def read_comorbidity_csv(filename: str):
    comorbidity_df = pd.read_csv(filename, index_col=0)
    column_names = [f"0-{comorbidity_df.columns[0]}"]
    for i in range(len(comorbidity_df.columns) - 1):
        column_names.append(
            f"{comorbidity_df.columns[i]}-{comorbidity_df.columns[i+1]}"
        )
    comorbidity_df.columns = column_names
    for column in comorbidity_df.columns:
        no_comorbidity = comorbidity_df[column].loc["no_condition"]
        should_have_comorbidity = 1 - no_comorbidity
        has_comorbidity = np.sum(comorbidity_df[column]) - no_comorbidity
        comorbidity_df[column].iloc[:-1] *= should_have_comorbidity / has_comorbidity

    return comorbidity_df.T


def convert_comorbidities_prevalence_to_dict(prevalence_female, prevalence_male):
    prevalence_reference_population = {}
    for comorbidity in prevalence_female.columns:
        prevalence_reference_population[comorbidity] = {
            "f": prevalence_female[comorbidity].to_dict(),
            "m": prevalence_male[comorbidity].to_dict(),
        }
    return prevalence_reference_population
