import h5py
import numpy as np
import random
import pandas as pd
import datetime
from pathlib import Path


class ReadLogger:
    def __init__(self, save_path: str = "results", file_name: str = "logger.hdf5"):
        self.save_path = save_path
        self.file_path = Path(self.save_path) / file_name
        self.load_population_data()
        self.load_infected_data()

    def load_population_data(self):
        with h5py.File(self.file_path, "r") as f:
            population = f["population"]
            self.n_people = population.attrs["n_people"]
            self.ids = population["id"][:]
            self.ages = population["age"][:]
            self.sexes = population["sex"][:]
            self.super_areas = population["super_area"][:].astype('U13')

    def load_infected_data(self,):
        with h5py.File(self.file_path, "r") as f:
            time_stamps = [key for key in f.keys() if key not in ("population", "hospitals", "locations")]
            ids = []
            symptoms = []
            for time_stamp in time_stamps:
                ids.append(f[time_stamp]["id"][:])
                symptoms.append(f[time_stamp]["symptoms"][:])
            self.infections_df = pd.DataFrame(
                {"time_stamp": time_stamps, "infected_id": ids, "symptoms": symptoms}
            )
            self.infections_df["time_stamp"] = pd.to_datetime(
                self.infections_df["time_stamp"]
            )
            self.infections_df.set_index("time_stamp", inplace=True)

    def process_symptoms(self, symptoms_df, n_people):
        df = pd.DataFrame()
        df["recovered"] = symptoms_df.apply(
            lambda x: np.count_nonzero(x.symptoms == 8), axis=1
        ).cumsum()
        df["dead"] = symptoms_df.apply(
            lambda x: np.count_nonzero(x.symptoms == 7), axis=1
        ).cumsum()
        # get rid of those that just recovered or died
        df["infected"] = symptoms_df.apply(
            lambda x: ((x.symptoms != 7) & (x.symptoms != 8)).sum(), axis=1
        )
        df["susceptible"] = n_people - df[["infected", "dead", "recovered"]].sum(
            axis=1
        )
        df["hospitalised"] = symptoms_df.apply(
            lambda x: np.count_nonzero(x.symptoms == 5), axis=1
        )
        df["intensive_care"] = symptoms_df.apply(
            lambda x: np.count_nonzero(x.symptoms == 6), axis=1
        )
        return df

    def world_summary(self,):
        return self.process_symptoms(self.infections_df, self.n_people)

    def super_area_summary(self):
        self.infections_df["super_areas"] = self.infections_df.apply(
            lambda x: self.super_areas[x.infected_id], axis=1
        )
        areas_df = []
        for area in np.unique(self.super_areas):
            area_df = pd.DataFrame()
            n_people_in_area = np.sum(self.super_areas == area)
            area_df["symptoms"] = self.infections_df.apply(
                lambda x: x.symptoms[x.super_areas == area], axis=1
            )
            area_df = self.process_symptoms(area_df, n_people_in_area)
            area_df["super_area"] = area
            areas_df.append(area_df)
        return pd.concat(areas_df)

    def age_summary(self, age_ranges):
        self.infections_df['age'] = self.infections_df.apply(
                                    lambda x: self.ages[x.infected_id], axis=1
                                     )
        ages_df = []
        for i in range(len(age_ranges)-1):
            age_df = pd.DataFrame()
            n_age = np.sum((self.ages>= age_ranges[i]) & ( self.ages < age_ranges[i+1]))
            age_df["symptoms"] = self.infections_df.apply(
                             lambda x: x.symptoms[(x.age >= age_ranges[i]) & (x.age < age_ranges[i+1])], axis=1
                            )
            age_df = self.process_symptoms(age_df, n_age)
            age_df['age_range'] = f'{age_ranges[i]}_{age_ranges[i+1]-1}'
            ages_df.append(age_df)
        return pd.concat(ages_df)

    def infection_duration(self):
        pass

    def draw_random_trajectories(self, time_window=50):
        starting_id = np.random.randint(0, high=len(self.infections_df))
        starting_time = self.infections_df.index[starting_id]
        end_date = starting_time + datetime.timedelta(days=time_window)
        mask = (self.infections_df.index > starting_time) & (
            self.infections_df.index <= end_date
        )
        random_trajectories = self.infections_df.loc[mask]
        random_trajectories = random_trajectories.apply(pd.Series.explode)
        random_ids = random.sample(list(random_trajectories.infected_id.unique()), 4)
        return [
            random_trajectories[random_trajectories["infected_id"] == random_id]
            for random_id in random_ids
        ]

    def load_infection_location(self):
        with h5py.File(self.file_path, "r") as f:
            infection_locations = f['locations']['infection_location'][:].astype('U13')
            counts = f['locations']['infection_counts'][:]
            n_locations = f['locations']['n_locations'][:]
        locations_df = pd.DataFrame({'location': infection_locations,
                              'counts': counts,
                              'n_locations': n_locations})
        locations_df['average_counts'] = locations_df['counts'] / locations_df['n_locations']
        locations_df.set_index('location', inplace=True)
        return locations_df



    def load_hospital_capacity(self):
        with h5py.File(self.file_path, "r") as f:
            hospitals = f["hospitals"]
            hospital_ids = []
            coordinates = []
            n_patients = []
            n_patients_icu = []
            for time_stamp in hospitals.keys():
                hospital_ids.append(hospitals[time_stamp]["hospital_id"][:])
                coordinates.append(hospitals[time_stamp]["coordinates"][:])
                n_patients.append(hospitals[time_stamp]["n_patients"][:])
                n_patients_icu.append(hospitals[time_stamp]["n_patients_icu"][:])
            time_stamps = list(hospitals.keys()) 

        hospitals_df = pd.DataFrame(
                {"time_stamp": time_stamps,
                "id": hospital_ids,
                "coordinates": coordinates,
                "n_patients": n_patients,
                "n_patients_icu": n_patients_icu,
                }
            )
        return hospitals_df.apply(pd.Series.explode)

