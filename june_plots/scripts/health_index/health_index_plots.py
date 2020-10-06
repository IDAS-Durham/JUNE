import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from june import paths


default_seroprev_filename = paths.data_path / "plotting/seroprev.dat"

default_icu_hosp_filename = paths.configs_path / "defaults/ICU_hosp.dat"
default_death_hosp_filename = paths.configs_path / "defaults/Death_hosp.dat"
default_hosp_cases_filename = paths.configs_path / "defaults/cases_hosp.dat"

plt.style.use('science')
class HealthIndexPlots:
    """
    Class for plotting health index plots
    """
    def zero_prevalence_plot(
        self,
        default_seroprev_filename=default_seroprev_filename
    ):
        seroprev_data=pd.read_csv(default_seroprev_filename,skiprows=1,sep=' ')
        age_min=seroprev_data['Age_bin_minimum'].values
        age_max=seroprev_data['Age_bin_max'].values
        seroprev_by_age=seroprev_data['Seroprevalence'].values
        seroprev=np.zeros(age_max[-1])
        for index in range(len(seroprev_by_age)):
           seroprev[age_min[index]:age_max[index]]=seroprev_by_age[index]
        
        
        f, ax = plt.subplots()
       # ax.tick_params(direction='in', which='both', top=True, right=True)#, labelsize=20)
        ax.plot(range(0,105), seroprev*100,linewidth=3,color='blue')
        ax.set_xlabel('Age')#,fontsize=30)
        ax.set_ylabel('Prevalence'+r'$[\%]$')#,fontsize=30)

        return ax
        #plt.savefig('../../plots/health_index/prevalence.pdf')
        
        
    def rates_plot(
        self, 
        hosp_filename=default_hosp_cases_filename,
        icu_filename=default_icu_hosp_filename,
        death_filename=default_death_hosp_filename 
    ):
        hosp_data=pd.read_csv(hosp_filename,sep=' ')
        
        r_hosp=hosp_data['ages'].values
        ratiof_hosp=hosp_data['hosp_cases_ratio_female'].values
        ratiom_hosp=hosp_data['hosp_cases_ratio_male'].values
        
        icu_data=pd.read_csv(icu_filename,sep=' ')
        r_icu=icu_data['ages'].values
        ratiof_icu=icu_data['icu_hosp_ratio_female'].values
        ratiom_icu=icu_data['icu_hosp_ratio_male'].values
        
        death_data=pd.read_csv(death_filename,sep=' ') 
        r_death=death_data['ages'].values
        ratiof_death=death_data['death_hosp_ratio_female'].values
        ratiom_death=death_data['death_hosp_ratio_male'].values
        
        #ax = plt.figure()
        #fig = plt.figure(figsize=(8, 8))
        f, ax = plt.subplots()
        #ax.tick_params(direction='in', which='both', top=True, right=True)#, labelsize=20) 
        ax.set_xlabel('Age [yr]') #, fontsize=20)
        


        ax.plot(r_hosp, ratiof_hosp,color='blue',linewidth=3,label=" HR female")
        ax.plot(r_hosp, ratiom_hosp,linestyle='--',color='blue',linewidth=3, label=" HR male")
        
        ax.plot(r_icu, ratiof_icu,color='green',linewidth=3,label="ICUR female")
        ax.plot(r_icu, ratiom_icu,linestyle='--',linewidth=3,color='green', label="ICUR male")
            
        ax.plot(r_death, ratiof_death,color='red',linewidth=3,label="DR female")
        ax.plot(r_death, ratiom_death,linestyle='--',color='red',linewidth=3, label="DR male")
        
        ax.legend() #prop={'size':16})
        return ax
        #plt.savefig('../../plots/health_index/rates.pdf',bbox_inches='tight')

