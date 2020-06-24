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

#Taken from ICNARC report
Survival_Rate_ICU = [
[0, 1.0],  #No death in icu reported.
[16, 78.6/100.0],
[40, 74.4/100.0],
[50, 59.3/100.0],
[60, 44.3/100.0],
[70, 32.9/100.0],
[80, 35.0/100.0]]


#Exces detahs
#https://www.gov.uk/government/publications/covid-19-review-of-disparities-in-risks-and-outcomes
Exces_Deaths = [
[0,1.0 ,1.0],  #No death in icu reported.
[15,1.0 ,1.0],
[45,79.8/100.0,81.2/100.0],
[64,83.3/100.0,83.7/100.0],
[75,81.8/100.0,84.7/100.0],
[85,63.6/100.0,75.1/100.0]]


class HealthIndexGenerator:
    """
    Computes  probabilities for (non-symptomatic, influenza-like symptoms, pneumonia, 
    hospitalisation, intensive care, fatality), using the age and sex of the subject.

    The probablities of hospitalisation,death and ICU are taken taken from fits made by 
    Miguel Icaza to the England data taken from several sources.


    We will assume that the symptomatic cases that do not need hospitalisation have either 
    mild symptoms or penumonia-like symptoms the percentage of those are distrubuted 
    according to the ratios in the RKI publication (table 1/column 2 of
     https://www.rki.de/DE/Content/Infekt/EpidBull/Archiv/2020/Ausgaben/17_20.pdf?__blob=publicationFile)
     
     
     """

    def __init__(self, poli_hosp: dict, poli_icu: dict, poli_deaths: dict,Asimpto_ratio=0.43):
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
        self.Poli_Hosp = poli_hosp
        self.Poli_ICU = poli_icu
        self.Poli_Deaths = poli_deaths
        self.Asimpto_ratio = Asimpto_ratio
        self.make_list()

    @classmethod
    def from_file(
            cls, polinome_filename: str = default_polinom_filename,asymptomatic_ratio=0.43
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
        

        return cls(poli_hosp, poli_icu, poli_deaths,asymptomatic_ratio)

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
        Computes the probability of having all 7 posible outcomes for all ages between 0 and 120. 
        And for male and female 
        
        Retruns:
             3D matrix of dimensions 2 X 120 X 7. With all the probabilities of all 6 
             outcomes for 120 ages and the 2 sex.
             
             For each gender and Age there are 7 numbers define: [N_1,N_2,N3,N4,N_5,N_6,N_7], 
             the idea is to select a random number r between 0 and 1. depending on how this random 
             number compares with our 7 numbers differents outcomes will happen
             - if  0<r<N_1  Asymptomatic
             - if  N_1<r<N_2 Mild symptoms
             - if N_2<r<N_3  Stays at home with pneoumonia symptoms and survives.
             - if N_3<r<N_4  Goes to the Hospital but not to ICU and survives.
             - if N_4<r<N_5  Goes to ICU ans survives.
             - if N_5<r<N_6  Stays at home with pneumonia and dies.
             - if N_6<r<N_7  Goes to the Hospital but not to ICU and dies.
             - if N_7<r<1    Goes to ICU and dies.
              

        """
        ages=np.arange(0,121,1)#from 0 to 120
        self.Prob_lists=np.zeros([2,121,7])
        self.Prob_lists[:,:,0]=self.Asimpto_ratio
        #Hosp,ICU,Death ratios
        
        ratio_Hosp_female=self.model(ages,self.Poli_Hosp[0])#Going to the Hospital but not to ICU
        ratio_ICU_female=self.model(ages,self.Poli_ICU[0])#Going to ICU
        ratio_Death_female=self.model(ages,self.Poli_Deaths[0])#Dying in Hospital (ICU+Hosp)
        
        ratio_Hosp_male=self.model(ages,self.Poli_Hosp[1])#Going to the Hospital but not to ICU
        ratio_ICU_male=self.model(ages,self.Poli_ICU[1])#Going to ICU
        ratio_Death_male=self.model(ages,self.Poli_Deaths[1])#Dying in Hospital (ICU+Hosp)
        
        #Probability of being simptomatic but not going to hospital
        No_Hosp_female=1.0-self.Asimpto_ratio-ratio_Hosp_female-ratio_ICU_female
        No_Hosp_male=1.0-self.Asimpto_ratio-ratio_Hosp_male-ratio_ICU_male
        
        #Probability of getting Pneumonia
        Prov_Pneumonia=np.ones(121)
        for pneumonia_index in range(len(RKIdata)-1):
               Boolean=(RKIdata[pneumonia_index][0]<=np.arange(0,121,1)) & (np.arange(0,121,1)<RKIdata[pneumonia_index+1][0])
               Prov_Pneumonia[Boolean]=RKIdata[pneumonia_index][1]
        Prov_Pneumonia[Prov_Pneumonia==1]=RKIdata[len(RKIdata)-1][1]
        
       
        #Provavility of  mild simptoms 
        self.Prob_lists[0,:,1]=No_Hosp_female*(1-Prov_Pneumonia)
        self.Prob_lists[1,:,1]=No_Hosp_male*(1-Prov_Pneumonia)
        
        #Provavility of Surviving ICU
        Survival_ICU=np.ones(121)
        for Survival_ICU_index in range(len(Survival_Rate_ICU)-1):
               Boolean=(Survival_Rate_ICU[Survival_ICU_index][0]<=np.arange(0,121,1)) & (np.arange(0,121,1)<Survival_Rate_ICU[Survival_ICU_index+1][0])
               Survival_ICU[Boolean]=Survival_Rate_ICU[Survival_ICU_index][1]
        Survival_ICU[np.arange(0,121,1)>=80]=Survival_Rate_ICU[len(Survival_Rate_ICU)-1][1] 
        
        
        self.Prob_lists[0,:,4]=ratio_ICU_female*Survival_ICU
        self.Prob_lists[1,:,4]=ratio_ICU_male*Survival_ICU
        
        #Provavility of Dying in ICU
        ICU_deaths_female=ratio_ICU_female*(1-Survival_ICU)
        ICU_deaths_male=ratio_ICU_male*(1-Survival_ICU)
        
        #self.Prob_lists[0,:,7]=ICU_deaths_female
        #self.Prob_lists[1,:,7]=ICU_deaths_male
        
        #provavility of Survinving  Hospital
 
        Deaths_Hosp_NoICU_female=ratio_Death_female-ICU_deaths_female
        Deaths_Hosp_NoICU_male=ratio_Death_male-ICU_deaths_male
        
        #If the death rate in ICU is around the number of deaths virtually everyone in that age dies in ICU.
        Deaths_Hosp_NoICU_female[Deaths_Hosp_NoICU_female<0]=1e-6
        Deaths_Hosp_NoICU_male[Deaths_Hosp_NoICU_male<0]=1e-6
        
        self.Prob_lists[0,:,3]=ratio_Hosp_female-Deaths_Hosp_NoICU_female
        self.Prob_lists[1,:,3]=ratio_Hosp_male-Deaths_Hosp_NoICU_male
        
        #provavility of dying in Hospital Without ICU
        self.Prob_lists[0,:,6]=Deaths_Hosp_NoICU_female
        self.Prob_lists[1,:,6]=Deaths_Hosp_NoICU_male
        '''
        provavility of dying in your home is the same as the number of deths above the mean of previous years
        that do not have covid 19 in the death certificate it is 23% according to 
        https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/889861/disparities_review.pdf
        '''
        #Excess Deaths
        Exces_Death_female=np.ones(121)
        Exces_Death_male=np.ones(121)
        for Exces_Deaths_index in range(len(Exces_Deaths)-1):
               Boolean=(Exces_Deaths[Exces_Deaths_index][0]<=np.arange(0,121,1)) & (np.arange(0,121,1)<Exces_Deaths[Exces_Deaths_index+1][0])
               Exces_Death_female[Boolean]=Exces_Deaths[Exces_Deaths_index][1]
               Exces_Death_male[Boolean]=Exces_Deaths[Exces_Deaths_index][2]
        
        
        Exces_Death_female[ages>=Exces_Deaths[-1][0]]=Exces_Deaths[-1][1]
        Exces_Death_male[ages>=Exces_Deaths[-1][0]]=Exces_Deaths[-1][2] 
        
        Deaths_at_home_female=ratio_Death_female*(1-Exces_Death_female)
        Deaths_at_home_male=ratio_Death_male*(1-Exces_Death_male)
        
        self.Prob_lists[0,:,5]=Deaths_at_home_female
        self.Prob_lists[1,:,5]=Deaths_at_home_male
        
        #Probability of having sever simptoms at home but surviving
        
        Prov_Home_Pneumonia_Female=No_Hosp_female*Prov_Pneumonia
        Prov_Home_Pneumonia_male=No_Hosp_male*Prov_Pneumonia
        
        self.Prob_lists[0,:,2]=Prov_Home_Pneumonia_Female-Deaths_at_home_female
        self.Prob_lists[1,:,2]=Prov_Home_Pneumonia_male-Deaths_at_home_male

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
        return np.cumsum(self.Prob_lists[sex][roundage])
