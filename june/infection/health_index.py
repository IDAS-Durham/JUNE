import numpy as np

from june import paths

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
    Computes probabilities for (asymptomatic, influenza-like symptoms, pneumonia, 
    hospitalisation, intensive care, fatality), using the age and sex of the subject.

    The probablities of hospitalisation,death and ICU are taken taken from fits made by 
    Miguel Icaza to the England data taken from several sources.

    We will assume that the symptomatic cases that do not need hospitalisation have either 
    mild symptoms or penumonia-like symptoms the percentage of those are distrubuted 
    according to the ratios in the RKI publication (table 1/column 2 of
    https://www.rki.de/DE/Content/Infekt/EpidBull/Archiv/2020/Ausgaben/17_20.pdf?__blob=publicationFile)
    """

    def __init__(
        self, poli_hosp: dict, poli_icu: dict, poli_deaths: dict, Asimpto_ratio=0.43
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
        self.Asimpto_ratio = Asimpto_ratio
        self.max_age = 80
        self.make_list()

    @classmethod
    def from_file(
        cls, polinome_filename: str = default_polinom_filename, asymptomatic_ratio=0.43
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

        return cls(poli_hosp, poli_icu, poli_deaths, asymptomatic_ratio)

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
             - if  N_5<r<N_6  Stays at home with pneumonia and dies.
             - if  N_6<r<N_7  Goes to the hospital but not to ICU and dies.
             - if  N_7<r<1    Goes to ICU and dies.
              

        """
        ages = np.arange(0, 121, 1)  # from 0 to 120
        self.prob_lists = np.zeros([2, 121, 7])
        self.prob_lists[:, :, 0] = self.Asimpto_ratio
        # hosp,ICU,death ratios

        ratio_hosp_female = self.model(
            ages, self.poli_hosp[0]
        )  # Going to the hospital but not to ICU
        ratio_icu_female = self.model(ages, self.poli_icu[0])  # Going to ICU
        ratio_death_female = self.model(
            ages, self.poli_deaths[0]
        )  # Dying in hospital (ICU+hosp)

        ratio_hosp_male = self.model(
            ages, self.poli_hosp[1]
        )  # Going to the hospital but not to ICU
        ratio_icu_male = self.model(ages, self.poli_icu[1])  # Going to ICU
        ratio_death_male = self.model(
            ages, self.poli_deaths[1]
        )  # Dying in hospital (ICU+hosp)

        # Probability of being simptomatic but not going to hospital
        no_hosp_female = 1.0 - self.Asimpto_ratio - ratio_hosp_female - ratio_icu_female
        no_hosp_male = 1.0 - self.Asimpto_ratio - ratio_hosp_male - ratio_icu_male

        # Probability of getting pneumonia
        prob_pneumonia = np.ones(121)
        for pneumonia_index in range(len(RKIdata) - 1):
            boolean = (RKIdata[pneumonia_index][0] <= np.arange(0, 121, 1)) & (
                np.arange(0, 121, 1) < RKIdata[pneumonia_index + 1][0]
            )
            prob_pneumonia[boolean] = RKIdata[pneumonia_index][1]
        prob_pneumonia[prob_pneumonia == 1] = RKIdata[len(RKIdata) - 1][1]

        # probavility of  mild simptoms
        self.prob_lists[0, :, 1] = no_hosp_female * (1 - prob_pneumonia)
        self.prob_lists[1, :, 1] = no_hosp_male * (1 - prob_pneumonia)

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

        prob_home_pneumonia_female = no_hosp_female * prob_pneumonia
        prob_home_pneumonia_male = no_hosp_male * prob_pneumonia

        self.prob_lists[0, :, 2] = prob_home_pneumonia_female - deaths_at_home_female
        self.prob_lists[1, :, 2] = prob_home_pneumonia_male - deaths_at_home_male

    def __call__(self, person):
        """
        Computes the probability of having all 8 posible outcomes for all ages between 0 and 120. 
        And for male and female 
        
        Retruns:
             3D matrix of dimensions 2 X 120 X 7. With all the probabilities of all 6 
             outcomes for 120 ages and the 2 sex.
        """
        if person.sex == "m":
            sex = 1
        else:
            sex = 0
        roundage = int(round(person.age))
        return np.cumsum(self.prob_lists[sex][roundage])
