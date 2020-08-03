import numpy as np
import pandas as pd
import yaml
from june.infection.symptom_tag import SymptomTag
from june import paths
from june.utils.parse_probabilities import parse_age_probabilities
from typing import Optional

default_polinom_filename = paths.configs_path / "defaults/health_index_ratios.txt"

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
        poli_hosp: dict,
        poli_icu: dict,
        poli_deaths: dict,
        asymptomatic_ratio=0.2,
        comorbidity_multipliers: Optional[dict] = None,
        prevalence_reference_population: Optional[dict] = None,
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
        self.poli_hosp = poli_hosp
        self.poli_icu = poli_icu
        self.poli_deaths = poli_deaths
        self.asymptomatic_ratio = asymptomatic_ratio
        self.max_age = 90
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
        polinome_filename: str = default_polinom_filename,
        asymptomatic_ratio=0.2,
        comorbidity_multipliers=None,
        prevalence_reference_population=None,
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

        polinoms = np.loadtxt(polinome_filename, skiprows=1)
        poli_hosp = np.array([polinoms[:, 0], polinoms[:, 1]])
        poli_icu = np.array([polinoms[:, 2], polinoms[:, 3]])
        poli_deaths = np.array([polinoms[:, 4], polinoms[:, 5]])

        return cls(
            poli_hosp,
            poli_icu,
            poli_deaths,
            asymptomatic_ratio,
            comorbidity_multipliers=comorbidity_multipliers,
            prevalence_reference_population=prevalence_reference_population,
        )

    @classmethod
    def from_file_with_comorbidities(
        cls,
        multipliers_path: str,
        male_prevalence_path: str,
        female_prevalence_path: str,
        polinome_filename: str = default_polinom_filename,
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
            polinome_filename=polinome_filename,
            asymptomatic_ratio=asymptomatic_ratio,
            comorbidity_multipliers=comorbidity_multipliers,
            prevalence_reference_population=prevalence_reference_population,
        )

    def model(self, age, poli):
        """
        Computes the probability of an outcome from the coefficients of the polinomal fit and for 
        a given array of ages
        Parameters:
        ----------
          age:
              array of ages where the probability should be computed.
          poli:
              The values C,C1,C2,C3
              of the polinomail fit defined to the probability of being hospitalised, 
              sent to an ICU unit or dying 
              the probaility (P) is computed as 
              P=10**(C+C1*Age+C2*Age**2+C3*Age**3)
          Returns:
             The probability P for all ages in the array "age".
        """
        c, c1, c2, c3 = poli
        age[age > self.max_age] = self.max_age
        return 10 ** (
            c + c1 * age + c2 * age ** 2 + c3 * age ** 3
        )  # The coefficients are a fit to the logarithmic model

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

        ratio_hosp_female_with_icu = self.model(
            ages, self.poli_hosp[0]
        )  # Going to the hospital
        ratio_icu_female = self.model(ages, self.poli_icu[0])  # Going to ICU
        ratio_death_female = self.model(
            ages, self.poli_deaths[0]
        )  # Dying in hospital (ICU+hosp)

        ratio_hosp_male_with_icu = self.model(
            ages, self.poli_hosp[1]
        )  # Going to the hospital
        ratio_icu_male = self.model(ages, self.poli_icu[1])  # Going to ICU
        ratio_death_male = self.model(
            ages, self.poli_deaths[1]
        )  # Dying in hospital (ICU+hosp)

        # Going to the hospital but not to ICU
        ratio_hosp_female = ratio_hosp_female_with_icu - ratio_icu_female
        ratio_hosp_male = ratio_hosp_male_with_icu - ratio_icu_male

        # Probability of being simptomatic but not going to hospital
        no_hosp_female = 1.0 - self.asymptomatic_ratio - ratio_hosp_female_with_icu
        no_hosp_male = 1.0 - self.asymptomatic_ratio - ratio_hosp_male_with_icu

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

        self.prob_lists[0, :, 4] = ratio_icu_female * survival_icu
        self.prob_lists[1, :, 4] = ratio_icu_male * survival_icu

        # probavility of Dying in icu
        icu_deaths_female = ratio_icu_female * (1 - survival_icu)
        icu_deaths_male = ratio_icu_male * (1 - survival_icu)

        # self.prob_lists[0,:,7]=icu_deaths_female
        # self.prob_lists[1,:,7]=icu_deaths_male

        # probability of Survinving  hospital

        deaths_hosp_noicu_female = ratio_death_female - icu_deaths_female
        deaths_hosp_noicu_male = ratio_death_male - icu_deaths_male

        # If the death rate in icu is around the number of deaths virtually everyone in that age dies in icu.
        deaths_hosp_noicu_female[deaths_hosp_noicu_female < 0] = 1e-6
        deaths_hosp_noicu_male[deaths_hosp_noicu_male < 0] = 1e-6

        self.prob_lists[0, :, 3] = ratio_hosp_female - deaths_hosp_noicu_female
        self.prob_lists[1, :, 3] = ratio_hosp_male - deaths_hosp_noicu_male

        # probability of dying in hospital Without icu
        self.prob_lists[0, :, 6] = deaths_hosp_noicu_female
        self.prob_lists[1, :, 6] = deaths_hosp_noicu_male
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

        deaths_at_home_female = ratio_death_female * (1 - excess_death_female)
        deaths_at_home_male = ratio_death_male * (1 - excess_death_male)

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
        if hasattr(self,'comorbidity_multipliers') and person.comorbidity is not None:
            probabilities = self.adjust_for_comorbidities(probabilities, person.comorbidity, person.age, person.sex)
        return np.cumsum(probabilities)

    def get_multiplier_from_reference_prevalence(
            self, prevalence_reference_population: dict, age: int, sex: str 
    )->float:
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
        for comorbidity in prevalence_reference_population.keys():
            weighted_multiplier += (
                self.comorbidity_multipliers[comorbidity]
                * self.prevalence_reference_population[comorbidity][sex][
                    age
                ]
            )
        return weighted_multiplier

    def adjust_for_comorbidities(self, probabilities: list, comorbidity: str, age: int, sex: str):
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
            self.prevalence_reference_population, age=age, sex=sex 
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
        p_mild = probabilities[:self.max_mild_symptom_tag].sum()
        p_severe = probabilities[self.max_mild_symptom_tag:].sum() + (1-probabilities.sum())
        p_severe_with_comorbidity = p_severe * effective_multiplier
        p_mild_with_comorbidity = 1 - p_severe_with_comorbidity
        probabilities_with_comorbidity[: self.max_mild_symptom_tag] = (
            probabilities[: self.max_mild_symptom_tag]
            * p_mild_with_comorbidity
            / p_mild
        )
        probabilities_with_comorbidity[self.max_mild_symptom_tag:] = (
            probabilities[self.max_mild_symptom_tag:]
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
