import os
import numpy as np
import pandas as pd
import argparse
import matplotlib.pyplot as plt

ward_prevalence_ethnicity = {
    "White": [4.8,5.,5.2],
    "Mixed": [7.1,8.9,11.1],
    "Asian": [11.0,11.9,12.8],
    "Black": [15.8,17.3,19.0],
    "Other": [10.2,12.3,14.7]
}

ward_prevalence_socio = {
    "1": [6.8,7.3,7.7],
    "2": [6.0,6.4,6.8],
    "3": [5.5,5.9,6.3],
    "4": [4.9,5.2,5.6],
    "5": [4.6,5.,5.4]
}

study_date = "2020-07-13"

def parse():
    """
    Parse arguments
    """

    parser = argparse.ArgumentParser(description=
                                     """
                                     Extract seroprevalence statistics and compare to studies
                                     """
    )

    parser.add_argument(
        "--record_path",
        dest = "record_path",
        help = "path to individual record",
        default = None,
    )

    parser.add_argument(
        "--records_path",
        dest = "records_path",
        help = "path to directory containing records",
        default = None
    )

    parser.add_argument(
        "--plots_path",
        dest = "plots_path",
        help = "path to where plots are to be saved",
        default = None
    )

    args = parser.parse_args()

    return args

class SeroPrevalence:

    def __init__(self, record_path, records_path=None, plots_path=None):

        self.record_path = record_path
        self.records_path = records_path
        self.plots_path = plots_path

        if self.record_path is None and self.records_path is None:
            raise ValueError("Both record_path and records_path cannont be None simultaneously")

    def load_data(self):

        print ("Loading data from: {}".format(self.record_path))

        self.people_df = pd.read_csv(self.record_path + "/people.csv")
        self.people_df.set_index('id', inplace=True)
        print ("People DataFrame loaded")

        self.infections_df = pd.read_csv(self.record_path + "/infections.csv")
        self.infections_df = self.infections_df.rename(columns={"Unnamed: 0": "id"})
        self.infections_df.set_index("id", inplace=True)
        print ("Infection DataFrame loaded")

    def prevalence_ethnicity(self):

        infected_by_ethnicity = self.infections_df.groupby(['ethnicity', 'timestamp']).size()
        n_by_ethnicity = self.people_df.groupby('ethnicity').size()

        prevalence_ethnicity = 100*infected_by_ethnicity.unstack(level=0).cumsum()/n_by_ethnicity
                                   
        return list(prevalence_ethnicity.loc[study_date])

    def prevalence_socio(self):

        infected_by_socio = self.infections_df.groupby(['socioeconomic_index', 'timestamp']).size()
        n_by_socio = self.people_df.groupby('socioeconomic_index').size()

        prevalence_socio = 100*infected_by_socio.unstack(level=0).cumsum()/n_by_socio

        return list(prevalence_socio.loc[study_date])

    def compare_seroprevalence_ethnicity(self):

        if self.records_path is not None:
            print ("Looping over records")

            prevalence_ethnicities = []
            prevalence_socios = []
            for i in os.listdir(self.records_path):
                self.record_path = self.records_path + "/" + i
                self.load_data()
                prevalence_ethnicity = self.prevalence_ethnicity()
                prevalence_socio = self.prevalence_socio()
                prevalence_ethnicities.append(prevalence_ethnicity)
                prevalence_socios.append(prevalence_socio)

            prevalence_ethnicity_mean = np.mean(prevalence_ethnicities, axis=0)
            prevalence_socio_mean = np.mean(prevalence_socio, axis=0)
            prevalence_ethnicity_std = np.std(prevalence_ethnicities, axis=0, ddof=1)
            prevalence_socio_std = np.std(prevalence_socio, axis=0, ddof=1)

        else:
            self.load_data()
            prevalence_ethnicity_mean = self.prevalence_ethnicity()
            prevalence_socio_mean = self.prevalence_socio()
            prevalence_ethnicity_std = 0.
            prevalence_socio_std = 0.

        print ("Plotting ethnicity seroprevalence comparison")

        fig = plt.figure()
            
        plt.errorbar(
            y = np.arange(len(ward_prevalence_ethnicity)),
            x = [prev[1] for eth, prev in ward_prevalence_ethnicity.items()],
            xerr = [
                [prev[1]-prev[0] for age, prev in ward_prevalence_ethnicity.items()],
                [prev[2]-prev[1] for age, prev in ward_prevalence_ethnicity.items()]
            ],
            fmt = "o",
            label = "Ward et al.",
            capsize = 5
        )

        plt.errorbar(
            y = np.arange(len(ward_prevalence_ethnicity)),
            x = prevalence_ethnicity_mean,
            xerr = prevalence_ethnicity_std,
            fmt = "o",
            label = "JUNE",
            capsize = 5
        )

        plt.yticks(np.arange(len(ward_prevalence_ethnicity)), labels = ward_prevalence_ethnicity.keys())
        plt.xlabel("Prevalence in group [%]")
        plt.legend()

        if self.plots_path is not None:
            print ("Saving out plots")
            plt.savefig(self.plots_path + "/ethnicities.png", dpi=150)
        
    def compare_seroprevalence(self):

        self.compare_seroprevalence_ethnicity()

            
if __name__ == "__main__":

    args = parse()

    seroprev = SeroPrevalence(args.record_path, args.records_path, args.plots_path)
    seroprev.compare_seroprevalence()

    
