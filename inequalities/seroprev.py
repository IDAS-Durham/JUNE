import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ward_prevalence_ethnicity = {
    'White': [4.8,5.,5.2],
    'Mixed': [7.1,8.9,11.1],
    'Asian': [11.0,11.9,12.8],
    'Black': [15.8,17.3,19.0],
    'Other': [10.2,12.3,14.7]
}

ward_prevalence_socio = {
    '1': [6.8,7.3,7.7],
    '2': [6.0,6.4,6.8],
    '3': [5.5,5.9,6.3],
    '4': [4.9,5.2,5.6],
    '5': [4.6,5.,5.4]
}

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

        self.people_df = pd.read_csv(self.record_path + "/people.csv")
        self.people_df.set_index('id', inplace=True)

        self.infections_df = pd.read_csv(self.record_path + "/infections.csv")
        self.infections_df = infections_df.rename(columns={"Unnamed: 0": "id"})
        self.infections_df.set_index("id", inplace=True)

    def prevalence_ethnicity(self):

        infected_by_ethnicity = self.infections_df.groupby(['ethnicity', 'timestamp']).size()
        n_by_ethnicity = self.people_df.groupby('ethnicity').size()

        prevalence_ethnicity = 100*infected_by_ethnicity.unstack(level=0).cumsum()/n_by_ethnicity

        return prevalence_ethnicity

    def prevalence_socio(self):

        infected_by_socio = self.infections_df.groupby(['socioeconomic_index', 'timestamp']).size()
        n_by_socio = self.people_df.groupby('socioeconomic_index').size()

        prevalence_socio = 100*infected_by_socio.unstack(level=0).cumsum()/n_by_socio

        return prevalence_socio

    def compare_seroprevalence(self):

        if self.records_path is not None:

            prevalence_ethnicities = []
            prevalence_socios = []
            for i in os.listdir(self.records_path):
                self.record_path = self.records_path + "/" + i
                prevalence_ethnicity = self.prevalence_ethnicity()
                prevalence_socio = self.prevalence_socio()

                # todo - work out exactly what is being appended here - currently it is the DataFrame but you don't want this
                prevalence_ethnicities.append(prevalence_ethnicity)
                prevalence_socios.append(prevalence_socio)

            # todo - check axes on mean and std operation
            prevalence_ethnicity_mean = np.mean(prevalence_ethnicities, axis=1)
            prevalence_socio_mean = np.mean(prevalence_socio, axis=1)
            prevalence_ethnicity_std = np.std(prevalence_ethnicities, axis=1, ddof=1)
            prevalence_socio_std = np.std(prevalence_socio, axis=1, ddof=1)

        else:
            prevalence_ethnicity_mean = self.prevalence_ethnicity()
            prevalence_socio_mean = self.prevalence_socio()
            prevalence_ethnicity_std = 0.
            prevalence_socio_std = 0.

        # todo - plotting against Ward 
            

if __name__ == "__main__":

    args = parse()
