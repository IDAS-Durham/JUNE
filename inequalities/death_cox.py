import numpy as np
import pandas as pd
import pickle
import matplotlib.pyplot as plt
from datetime import datetime
from tqdm import tqdm

from lifelines import CoxPHFitter

study_start = datetime(2020, 2, 1, 0, 0)
study_end = datetime(2020, 5, 16, 0, 0)
study_duration = (study_end - study_start).days

def parse():
    """
    Parse arguments
    """

    parser = argparse.ArgumentParser(description=
                                     """
                                     Train Cox regression hazard models for deaths by ethnicity and socioeconomic index
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
        "--se_control",
        dest = "se_control",
        help = "control for socioeconomic index in ethnicity models",
        default = False
    )

    args = parser.parse_args()

    return args

class DeathCox:

    def __init__(self, record_path, records_path=None, se_control=False):

        self.record_path = record_path
        self.records_path = records_path
        self.se_control = se_control

        if self.record_path is None and self.records_path is None:
            raise ValueError("Both record_path and records_path cannont be None simultaneously")

    def load_data(self):

        print ("Loading data from: {}".format(self.record_path))

        self.people_df = pd.read_csv(self.record_path + "/people.csv")
        self.people_df.set_index('id', inplace=True)
        print ("People DataFrame loaded")

        self.deaths_df = pd.read_csv(self.record_path + "/deaths.csv")
        self.deaths_df = self.deaths_df.rename(columns={"Unnamed: 0": "id"})
        self.deaths_df.set_index("id", inplace=True)
        print ("Deaths DataFrame loaded")

    def process_data(self):

        self.people_df = self.people_df.sort_index()

        print ("Adding death data to people DataFrame")
        people_df_died = list(np.zeros(len(self.people_df)))
        people_df_days_dead = list(np.ones(len(self.people_df)) * study_duration)
        for idx, row in tqdm(self.deaths_df.iterrows(), total = len(deaths_df)):
            days_dead = (datetime.strptime(row["timestamp"], "%Y-%m-%d") - study_start).days
            if days_dead < study_duration:
                people_df_died[idx] = 1
                people_df_days_dead[idx] = days_dead

        self.people_df["died"] = list(np.array(people_df_died).astype(int))
        self.people_df["days"] = list(np.array(people_df_days_dead).astype(int))

        print ("Processing categorical variables")
        
        self.people_df.loc[self.people_df["sex"] == "f", "sex"] = 0
        self.people_df.loc[self.people_df["sex"] == "m", "sex"] = 1

        self.people_df.loc[self.people_df["ethnicity"] == "A", "ethnicity"] = 0
        self.people_df.loc[self.people_df["ethnicity"] == "B", "ethnicity"] = 1
        self.people_df.loc[self.people_df["ethnicity"] == "C", "ethnicity"] = 2
        self.people_df.loc[self.people_df["ethnicity"] == "D", "ethnicity"] = 3
        self.people_df.loc[self.people_df["ethnicity"] == "E", "ethnicity"] = 4

        if self.se_control:
            self.people_cox_df = self.people_df[["age", "sex", "ethnicity", "socioeconomic_index", "died", "days"]]
        else:
            self.people_cox_df = self.people_df[["age", "sex", "ethnicity", "died", "days"]]

        print ("Data processed")

    def train_cox_ethnicity(self):

        people_cox_b = self.people_cox_df[people_cox_df["ethnicity"].isin([0,1])]
        people_cox_c = self.people_cox_df[people_cox_df["ethnicity"].isin([0,2])]
        people_cox_d = self.people_cox_df[people_cox_df["ethnicity"].isin([0,3])]
        people_cox_e = self.people_cox_df[people_cox_df["ethnicity"].isin([0,4])]

        people_cox_c.loc[people_cox_c["ethnicity"] == 2, "ethnicity"] = 1
        people_cox_d.loc[people_cox_d["ethnicity"] == 3, "ethnicity"] = 1
        people_cox_e.loc[people_cox_e["ethnicity"] == 4, "ethnicity"] = 1

        print ("Training Cox model on ethnicity: B")
        cph_b = CoxPHFitter()
        cph_b.fit(people_cox_b, duration_col="days", event_col="died", show_progress=True)

        if self.se_control:
            save_path = self.record_path + "/cph_b_se_control.pickle"
        else:
            save_path = self.record_path + "/cph_b.pickle"
        with open(save_path, 'wb') as f:
            pickle.dump(cph_b, f)
        print ("Model saved")

        print ("Training Cox model on ethnicity: C")
        cph_c = CoxPHFitter()
        cph_c.fit(people_cox_c, duration_col="days", event_col="died", show_progress=True)

        if self.se_control:
            save_path = self.record_path + "/cph_c_se_control.pickle"
        else:
            save_path = self.record_path + "/cph_c.pickle"
        with open(save_path, 'wb') as f:
            pickle.dump(cph_c, f)
        print ("Model saved")

        print ("Training Cox model on ethnicity: D")
        cph_d = CoxPHFitter()
        cph_d.fit(people_cox_d, duration_col="days", event_col="died", show_progress=True)

        if self.se_control:
            save_path = self.record_path + "/cph_d_se_control.pickle"
        else:
            save_path = self.record_path + "/cph_d.pickle"
        with open(save_path, 'wb') as f:
            pickle.dump(cph_d, f)
        print ("Model saved")
            
        print ("Training Cox model on ethnicity: E")
        cph_e = CoxPHFitter()
        cph_e.fit(people_cox_e, duration_col="days", event_col="died", show_progress=True)

        if self.se_control:
            save_path = self.record_path + "/cph_e_se_control.pickle"
        else:
            save_path = self.record_path + "/cph_e.pickle"
        with open(save_path, 'wb') as f:
            pickle.dump(cph_e, f)
        print ("Model saved")

    def train_all(self):

         if self.records_path is not None:
            print ("Looping over records")

            for i in os.listdir(self.records_path):
                self.record_path = self.records_path + "/" + i
                self.load_data()
                self.process_data()
                self.train_cox_ethnicity()

         else:
             self.load_data()
             self.process_data()
             self.train_cox_ethnicity()

        
if __name__ == "__main__":

    args = parse()

    death_cox = DeathCox(args.record_path, args.records_path, args.se_control)
    death_cox.train_all()
