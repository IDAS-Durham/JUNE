import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from june import paths
from june.demography import Person
from june.infection import HealthIndexGenerator, InfectionSelector, SymptomTag


default_seroprev_filename = paths.data_path / "plotting/seroprev.dat"

default_transmission = paths.configs_path / "defaults/transmission/XNExp.yaml"

class HealthIndexPlots:
    """
    Class for plotting health index plots
    """

    def __init__(self, colors):
        self.colors = colors

    def sero_prevalence_plot(self, default_seroprev_filename=default_seroprev_filename):
        seroprev_data = pd.read_csv(default_seroprev_filename, skiprows=1, sep=" ")
        age_min = seroprev_data["Age_bin_minimum"].values
        age_max = seroprev_data["Age_bin_max"].values
        seroprev_by_age = seroprev_data["Seroprevalence"].values
        seroprev = np.zeros(age_max[-1])
        for index in range(len(seroprev_by_age)):
            seroprev[age_min[index] : age_max[index]] = seroprev_by_age[index]

        f, ax = plt.subplots()
        ax.plot(range(0, 105), seroprev * 100, linewidth=2, color=self.colors['general_4'])
        ax.set_xlabel("Age")
        ax.set_ylabel("Prevalence [\%]")

        return ax

    def rates_plot(self,):
        ages = np.arange(100)
        male_hospitalisation_rate, female_hospitalisation_rate = [], []
        male_icu_rate, female_icu_rate = [], []
        male_death_rate, female_death_rate = [], []
        for age in ages:
            health_index_generator = HealthIndexGenerator.from_file()
            male = Person.from_attributes(age=age, sex="m")
            female = Person.from_attributes(age=age, sex="f")
            male_probabilities = np.diff(
                health_index_generator(male), prepend=0, append=1
            )
            male_hospitalisation_rate.append(male_probabilities[[3, 6]].sum())
            male_icu_rate.append(male_probabilities[[4, 7]].sum())
            male_death_rate.append(male_probabilities[[5, 6, 7]].sum())
            female_probabilities = np.diff(
                health_index_generator(female), prepend=0, append=1
            )
            female_hospitalisation_rate.append(female_probabilities[[3, 6]].sum())
            female_icu_rate.append(female_probabilities[[4, 7]].sum())
            female_death_rate.append(female_probabilities[[5, 6, 7]].sum())

        f, ax = plt.subplots()
        ax.set_xlabel("Age")
        ax.plot(
            ages,
            female_hospitalisation_rate,
            color=self.colors['general_1'],
            linewidth=2,
            label=" HR female",
        )
        ax.plot(
            ages,
            male_hospitalisation_rate,
            linestyle="--",
            color=self.colors['general_1'],
            linewidth=2,
            label=" HR male",
        )

        ax.plot(ages, female_icu_rate, color=self.colors['general_2'], linewidth=3, label="ICUR female")
        ax.plot(
            ages,
            male_icu_rate,
            linestyle="--",
            linewidth=2,
            color=self.colors['general_2'],
            label="ICUR male",
        )

        ax.plot(ages, female_death_rate, color=self.colors['general_3'], linewidth=3, label="DR female")
        ax.plot(
            ages,
            male_death_rate,
            linestyle="--",
            color=self.colors['general_3'],
            linewidth=2,
            label="DR male",
        )

        ax.legend()
        return ax

    def get_infectiousness(self, person, final_time):
        transmission = []
        times = []
        time = 0.0
        delta_time = 0.1
        while time < final_time:
            transmission.append(person.infection.transmission.probability)
            person.infection.update_symptoms_and_transmission(time + delta_time)
            time += delta_time
            times.append(time)
        return times, transmission

    def infectiousness(self,):
        symptom_tags = ["severe", "mild", "asymptomatic"]
        infection_selector = InfectionSelector.from_file(
            transmission_config_path=default_transmission
        )
        f, ax = plt.subplots()
        random_person = Person.from_attributes(sex="m", age=50)
        infection_selector.infect_person_at_time(random_person, 0.0)
        random_person.infection.symptoms.tag = getattr(SymptomTag, "severe")

        N_tries = 10
        ### The axvline sometimes fails. Until a random seed is fixed, here's an exceptionally
        ### ugly fix.
        for i in range(N_tries):
            try:
                ax.axvline(x=random_person.infection.time_of_symptoms_onset, 
                        linestyle="dashed",
                        color='gray',
                        alpha=0.3,
                        label='time of symptoms onset',
                        linewidth=2,
                )
                break
            except:
                pass

        times, transmissions = self.get_infectiousness(random_person, 14.0)
        ax.plot(times, transmissions, label="severe", linewidth=2, color=self.colors['general_1'])
        ax.plot(
            times,
            infection_selector.mild_infectious_factor.value * np.array(transmissions),
            label="mild",
            linewidth=2,
            color=self.colors['general_2']
        )
        ax.plot(
            times,
            infection_selector.asymptomatic_infectious_factor.value
            * np.array(transmissions),
            label="asymptomatic",
            linewidth=2,
            color=self.colors['general_3']
        )
        ax.set_xlabel("Days from infection")

        ax.set_ylabel("Infectivity")
        ax.legend(bbox_to_anchor = (0.5,1.02),loc='lower center',ncol=2)
        f.subplots_adjust(top=0.80)
        
        return ax
