import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from june import paths


default_seroprev_filename = paths.configs_path / "data/plotting/seroprev.dat"

default_icu_hosp_filename = paths.configs_path / "defaults/ICU_hosp.dat"
default_death_hosp_filename = paths.configs_path / "defaults/Death_hosp.dat"
default_hosp_cases_filename = paths.configs_path / "defaults/cases_hosp.dat"






plt.style.use('science')
class HealthIndexPlots:
    """
    Class for plotting helath index plots

    """
def zero_prevalence_plot(
            self,default_seroprev_filename
            ):
        seroprev_data=pd.read_csv(default_seroprev_filename,skiprows=1,sep=' ')
        age_min=seroprev_data['Age_bin_minimum'].values
        age_max=seroprev_data['Age_bin_max'].values
        seroprev_by_age=seroprev_data['Seroprevalence'].values
        seroprev=np.zeros(age_max[-1])
        for index in range(len(seroprev_by_age)):
           seroprev[age_min[index]:age_max[index]]=seroprev_by_age[index]
        
        plt.figure()
        fig = plt.figure(figsize=(8, 8))
        plt.tick_params(direction='in', which='both', top=True, right=True, labelsize=20)
        plt.plot(range(0,105), seroprev*100,linewidth=3,color='blue')
        plt.xlabel('Age',fontsize=30)
        plt.ylabel('Prevalence'+r'$[\%]$',fontsize=30)
        plt.savefig('prevalence.pdf')
        
        
    def rates_plot(
            self,default_hosp_filename
            ):
       hosp_data=pd.read_csv(default_hosp_filename,sep=' ')
    
       r_hosp=hosp_data['ages'].values
       ratiof_hosp=hosp_data['hosp_cases_ratio_female'].values
       ratiom_hosp=hosp_data['hosp_cases_ratio_male'].values
       
       icu_data=pd.read_csv(default_icu_filename,sep=' ')
       r_icu=icu_data['ages'].values
       ratiof_icu=icu_data['icu_hosp_ratio_female'].values
       ratiom_icu=icu_data['icu_hosp_ratio_male'].values
    
       death_data=pd.read_csv(default_death_filename,sep=' ') 
       r_death=death_data['ages'].values
       ratiof_death=death_data['death_hosp_ratio_female'].values
       ratiom_death=death_data['death_hosp_ratio_male'].values
       
       ax = plt.figure()
       fig = plt.figure(figsize=(8, 8))
       plt.tick_params(direction='in', which='both', top=True, right=True, labelsize=20) 
       plt.xlabel('Age [yr]', fontsize=20)
       


       plt.plot(r_hosp, ratiof_hosp,color='blue',linewidth=3,label=" HR female")
       plt.plot(r_hosp, ratiom_hosp,linestyle='--',color='blue',linewidth=3, label=" HR male")
       
       plt.plot(r_icu, ratiof_icu,color='green',linewidth=3,label="ICUR female")
       plt.plot(r_icu, ratiom_icu,linestyle='--',linewidth=3,color='green', label="ICUR male")
        
       plt.plot(r_death, ratiof_death,color='red',linewidth=3,label="DR female")
       plt.plot(r_death, ratiom_death,linestyle='--',color='red',linewidth=3, label="DR male")
       
       plt.legend(prop={'size':16})
       plt.savefig('hosp_rate.pdf',bbox_inches='tight')
       
