import numpy as np

from june import paths

default_polinom_filename = (
        paths.configs_path / "defaults/health_index_ratios.txt"
)

RKIdata = [
    [0.0, 4.0 / 100.0],
    [5.0, 4.0 / 100.0],
    [15.0, 1.5 / 100.0],
    [35.0, 4.0 / 100.0],
    [60.0, 14.0 / 100.0],
    [80.0, 46.0 / 100.0],
]


class HealthIndexGenerator:
    """
    Computes  probabilities for (non-symptomatic, influenza-like symptoms, pneumonia, 
    hospitalisation, intensive care, fatality), using the age and sex of the subject.

    The probablities of hospitalisation,death and ICU are taken taken from fits made by 
    Miguel Icaza to the Spanish data taken from:

    https://github.com/datadista/datasets/tree/master/COVID%2019


    We will assume that the symptomatic cases that do not need hospitalisation have either 
    influenza-like or penumonia-like symptoms the percentage of those are distrubuted 
    according to the ratios in the RKI publication (table 1/column 2 of
     https://www.rki.de/DE/Content/Infekt/EpidBull/Archiv/2020/Ausgaben/17_20.pdf?__blob=publicationFile)

     For this I assume a "pneumonia probability for the asyptomatic, non-hospitalised cases
     given by Pneumonia/(ILI+Peumonia) - probably too crude.
     """

    def __init__(self, asymptomatic_ratio: float, poli_hosp: dict, poli_icu: dict, poli_deaths: dict):
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
        - asymptomatic_ratio:
          The percentage of the population that will be asymptomatic, we fixed it to 
          43% and assume that is age-independent.  This assumptions comes from 
          Vo et al 2019 ( https://doi.org/10.1101/2020.04.17.20053157 ).
          
        """
        self.poli_hosp = poli_hosp
        self.poli_icu = poli_icu
        self.poli_deaths = poli_deaths
        self.asymptomatic_ratio = asymptomatic_ratio
        self.baseline_asymptomatic_ratio = 0.43
        self.make_list()

    @classmethod
    def from_file(
            cls, asymptomatic_ratio: float=0.43, polinome_filename: str = default_polinom_filename,
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

        return cls(asymptomatic_ratio,poli_hosp, poli_icu, poli_deaths)

    def model(self, age, poli):
        """
        Computes the probability of an outcome from the coefficients of the polinomal fit and for 
        a given array of ages

        Parameters:
        ----------
          age:
              array of ages where the probability should be computed.
          Poli:
              The values C,C1,C2,C3
              of the polinomail fit defined to the probability of being hospitalised, 
              sent to an ICU unit or dying 
              the probaility (P) is computed as 
              P=10**(C+C1*Age+C2*Age**2+C3*Age**3)
          Returns:
             The probability P for all ages in the array "age".
        """
        C, C1, C2, C3 = poli
        age[age > 85.0] = 85.0
        return 10 ** (
                C + C1 * age + C2 * age ** 2 + C3 * age ** 3
        )  # The coefficients are a fit to the logarithmic model

    def make_list(self):
        """
        Computes the probability of having all 6 posible outcomes for all ages between 0 and 120. 
        And for male and female 
        
        Retruns:
             3D matrix of dimensions 2 X 120 X 6. With all the probabilities of all 6 
             outcomes for 120 ages and the 2 sex.
        """

        ages = np.arange(0, 121, 1)  # from 0 to 120
        self.prob_lists = np.zeros([2, 121, 5])

        self.prob_lists[:, :, 0] = self.asymptomatic_ratio
        hosp_ratio_female =  self.model(ages, self.poli_hosp[0])
        hosp_ratio_male =  self.model(ages, self.poli_hosp[1])

        icu_ratio_female = self.model(ages, self.poli_icu[0])
        icu_ratio_male = self.model(ages, self.poli_icu[1])


        death_ratio_female = self.model(ages, self.poli_deaths[0])
        death_ratio_male = self.model(ages, self.poli_deaths[1])


        # This makes sure that the ICU<deaths
        Boolean_icu_female = (death_ratio_female > icu_ratio_female)  # If the DEath ratio is larger that the ICU ratio
        Boolean_icu_male = (death_ratio_male > icu_ratio_male)

        icu_ratio_female[Boolean_icu_female] = death_ratio_female[Boolean_icu_female]
        icu_ratio_male[Boolean_icu_male] = death_ratio_male[Boolean_icu_male]        
           
        # This makes sure that HOsp<ICU
 
        Boolean_hosp_female = (icu_ratio_female > hosp_ratio_female)  # If the DEath ratio is larger that the ICU ratio
        Boolean_hosp_male = (icu_ratio_male > hosp_ratio_male)

        hosp_ratio_female[Boolean_hosp_female] = icu_ratio_female[Boolean_hosp_female]
        hosp_ratio_male[Boolean_hosp_male] = icu_ratio_male[Boolean_hosp_male]

        asymptomatic_correction = (1+self.baseline_asymptomatic_ratio)/(1+self.asymptomatic_ratio)


        self.prob_lists[0, :, 2] = 1 - hosp_ratio_female*asymptomatic_correction
        self.prob_lists[1, :, 2] = 1 - hosp_ratio_male*asymptomatic_correction

        self.prob_lists[0, :, 3] = 1 - icu_ratio_female*asymptomatic_correction
        self.prob_lists[1, :, 3] = 1 - icu_ratio_male*asymptomatic_correction

        self.prob_lists[0, :, 4] = 1 - death_ratio_female*asymptomatic_correction
        self.prob_lists[1, :, 4] = 1 - death_ratio_male*asymptomatic_correction


        No_hosp_prov = np.array(
            [
                self.prob_lists[0, :, 2] - self.asymptomatic_ratio,
                self.prob_lists[1, :, 2] - self.asymptomatic_ratio,
            ]
        )
        Pneumonia = np.ones(121)
        for pneumonia_index in range(len(RKIdata) - 1):
            Boolean = (RKIdata[pneumonia_index][0] <= np.arange(0, 121, 1)) & (
                    np.arange(0, 121, 1) < RKIdata[pneumonia_index + 1][0]
            )
        Pneumonia[Boolean] = RKIdata[pneumonia_index][1]
        Pneumonia[Pneumonia == 1] = RKIdata[len(RKIdata) - 1][1]

        self.prob_lists[0, :, 1] = self.asymptomatic_ratio + No_hosp_prov[0] * (
                1 - Pneumonia
        )
        self.prob_lists[1, :, 1] = self.asymptomatic_ratio + No_hosp_prov[1] * (
                1 - Pneumonia
        )

    def __call__(self, person):
        """
        Computes the probability of having all 6 posible outcomes for all ages between 0 and 120. 
        And for male and female 
        
        Retruns:
             3D matrix of dimensions 2 X 120 X 6. With all the probabilities of all 6 
             outcomes for 120 ages and the 2 sex.
        """
        
        sex = 1
        if person.sex == "f":
            sex = 0
        roundage = int(round(person.age))
        return self.prob_lists[sex][roundage]
