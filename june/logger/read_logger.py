import h5py
import numpy as np
from random import sample, randint
import pandas as pd
import datetime
from pathlib import Path
from typing import List

from june.infection import SymptomTag
from june import paths


class ReadLogger:
    def __init__(
        self,
        output_path: str = "results",
        output_file_name: str = "logger.hdf5",
        light_logger: bool = False,
    ):
        """
        Read hdf5 file saved by the logger, and produce useful data frames

        Parameters
        ----------
        output_path:
            path to simulation's output
        output_file_name:
            name of file saved by simulation
        """
        self.output_path = output_path
        self.file_path = Path(self.output_path) / output_file_name
        self.light_logger = light_logger
        self.load_population_data(self.light_logger)
        self.load_infected_data()
        self.load_infection_location()
        self.start_date = min(self.infections_df.index)
        self.end_date = max(self.infections_df.index)

    def load_population_data(self, light_logger):
        """
        Load data related to population (age, sex, ...)
        """
        with h5py.File(self.file_path, "r", libver="latest", swmr=True) as f:
            population = f["population"]
            self.n_people = population.attrs["n_people"]
            if not light_logger:
                self.ids = population["id"][:]
                self.ages = population["age"][:]
                self.sexes = population["sex"][:]
                self.super_areas = population["super_area"][:].astype("U13")
                self.ethnicities = population["ethnicity"][:]
                self.socioeconomic_indices = population["socioeconomic_index"][:]

    def load_infected_data(self,):
        """
        Load data on infected people over time and convert to a data frame ``self.infections_df``
        """
        with h5py.File(self.file_path, "r", libver="latest", swmr=True) as f:
            time_stamps = [
                key
                for key in f.keys()
                if key not in ("population", "hospitals", "locations", "parameters")
            ]
            ids = []
            symptoms = []
            n_secondary_infections = []
            for time_stamp in time_stamps:
                ids.append(f[time_stamp]["id"][:])
                symptoms.append(f[time_stamp]["symptoms"][:])
                n_secondary_infections.append(
                    f[time_stamp]["n_secondary_infections"][:]
                )
            self.infections_df = pd.DataFrame(
                {
                    "time_stamp": time_stamps,
                    "infected_id": ids,
                    "symptoms": symptoms,
                    "n_secondary_infections": n_secondary_infections,
                }
            )
            self.infections_df["time_stamp"] = pd.to_datetime(
                self.infections_df["time_stamp"]
            )
            self.infections_df.set_index("time_stamp", inplace=True)

    def subtract_previous(self, row, hospitalised_id, prev_hospitalised_id):
        try:
            return len(
                set(hospitalised_id.loc[row.name])
                - set(prev_hospitalised_id.loc[row.name])
            )
        except:
            return len(set(hospitalised_id.loc[row.name]))

    def process_symptoms(
        self, symptoms_df: pd.DataFrame, n_people: int
    ) -> pd.DataFrame:
        """
        Given a dataframe with time stamp and a list of symptoms representing the symptoms of every infected 
        person, produce a summary with the number of recovered, dead, infected, susceptible 
        and hospitalised people

        Parameters
        ----------
        symptoms_df:
            data frame with a list of symptoms per time step
        n_people:
            number of total people (including susceptibles)
        Returns
        -------
        A data frame whose index is the date recorded, and columns are number of recovered, dead, infected...
        """
        dead_symptoms = [
            SymptomTag.dead_home,
            SymptomTag.dead_icu,
            SymptomTag.dead_hospital,
        ]
        df = pd.DataFrame()
        df["daily_recovered"] = symptoms_df.apply(
            lambda x: np.count_nonzero(x.symptoms == SymptomTag.recovered), axis=1
        )  # .cumsum()
        df["daily_deaths_home"] = symptoms_df.apply(
            lambda x: np.count_nonzero(x.symptoms == SymptomTag.dead_home), axis=1
        )  # .cumsum()
        df["daily_deaths_hospital"] = symptoms_df.apply(
            lambda x: np.count_nonzero(x.symptoms == SymptomTag.dead_hospital), axis=1
        )  # .cumsum()
        df["daily_deaths_icu"] = symptoms_df.apply(
            lambda x: np.count_nonzero(x.symptoms == SymptomTag.dead_icu), axis=1
        )  # .cumsum()
        df['daily_deaths'] = df[['daily_deaths_home', 'daily_deaths_hospital', 'daily_deaths_icu']].sum(axis=1)
        # get rid of those that just recovered or died
        df["current_infected"] = symptoms_df.apply(
            lambda x: (
                (x.symptoms != SymptomTag.recovered)
                & (~np.isin(x.symptoms, dead_symptoms))
            ).sum(),
            axis=1,
        )
        df["current_dead"] = df["daily_deaths"].cumsum()
        df["current_recovered"] = df["daily_recovered"].cumsum()
        df["current_susceptible"] = n_people - df[
            ["current_infected", "current_dead", "current_recovered"]
        ].sum(axis=1)
        df["current_hospitalised"] = symptoms_df.apply(
            lambda x: np.count_nonzero(x.symptoms == SymptomTag.hospitalised), axis=1
        )
        df["current_intensive_care"] = symptoms_df.apply(
            lambda x: np.count_nonzero(x.symptoms == SymptomTag.intensive_care), axis=1
        )
        flat_df = self.infections_df[["symptoms", "infected_id"]].apply(
            lambda x: x.explode() if x.name in ["infected_id", "symptoms"] else x
        )
        flat_hospitalised_df = flat_df[
            flat_df["symptoms"] == SymptomTag.hospitalised
        ].drop_duplicates(keep="first")
        df["daily_hospital_admissions"] = flat_hospitalised_df.groupby(
            flat_hospitalised_df.index
        ).size()
        df["daily_hospital_admissions"] = df["daily_hospital_admissions"].fillna(0.0)
        df["daily_infections"] = (
            -df["current_susceptible"]
            .diff()
            .fillna(-df["current_infected"][0])
            .astype(int)
        )
        return df

    def world_summary(self) -> pd.DataFrame:
        """
        Generate a summary at the world level, on how many people are recovered, dead, infected,
        susceptible, hospitalised or in intensive care, per time step.

        Returns
        -------
        A data frame whose index is the date recorded, and columns are number of recovered, dead, infected...
        """
        return self.process_symptoms(self.infections_df, self.n_people)

    def super_area_summary(self) -> pd.DataFrame:
        """
        Generate a summary for super areas, on how many people are recovered, dead, infected,
        susceptible, hospitalised or in intensive care, per time step.

        Returns
        -------
        A data frame whose index is the date recorded, and columns are super area, number of recovered, 
        dead, infected...
        """
        self.infections_df["super_areas"] = self.infections_df.apply(
            lambda x: self.super_areas[x.infected_id], axis=1
        )
        unique_super_areas = np.unique(self.super_areas)
        areas_df = []
        for area in unique_super_areas:
            area_df = pd.DataFrame()
            n_people_in_area = np.sum(self.super_areas == area)
            area_df["symptoms"] = self.infections_df.apply(
                lambda x: x.symptoms[x.super_areas == area], axis=1
            )
            area_df["infected_id"] = self.infections_df.apply(
                lambda x: x.infected_id[x.super_areas == area], axis=1
            )
            area_df = self.process_symptoms(area_df, n_people_in_area)
            area_df["super_area"] = area
            areas_df.append(area_df)
        return pd.concat(areas_df)

    def age_summary(self, age_ranges: List[int]) -> pd.DataFrame:
        """
        Generate a summary per age range, on how many people are recovered, dead, infected,
        susceptible, hospitalised or in intensive care, per time step.

        Parameters
        ----------
        age_ranges:
            list of ages that determine the boundaries of the bins.
            Example: [0,5,10,100] -> Bins : [0,4] , [5,9], [10,99]

        Returns
        -------
        A data frame whose index is the date recorded, and columns are super area, number of recovered, 
        dead, infected...
        """
        self.infections_df["age"] = self.infections_df.apply(
            lambda x: self.ages[x.infected_id], axis=1
        )
        ages_df = []
        for i in range(len(age_ranges) - 1):
            age_df = pd.DataFrame()
            n_age = np.sum(
                (self.ages >= age_ranges[i]) & (self.ages < age_ranges[i + 1])
            )
            age_df["symptoms"] = self.infections_df.apply(
                lambda x: x.symptoms[
                    (x.age >= age_ranges[i]) & (x.age < age_ranges[i + 1])
                ],
                axis=1,
            )
            age_df["infected_id"] = self.infections_df.apply(
                lambda x: x.infected_id[
                    (x.age >= age_ranges[i]) & (x.age < age_ranges[i + 1])
                ],
                axis=1,
            )

            age_df = self.process_symptoms(age_df, n_age)
            age_df["age_range"] = f"{age_ranges[i]}_{age_ranges[i+1]-1}"
            ages_df.append(age_df)
        return pd.concat(ages_df)

    def draw_symptom_trajectories(
        self, window_length: int = 50, n_people: int = 4
    ) -> pd.DataFrame:
        """
        Get data frame with symptoms trajectories of n_people random people that are infected 
        in a time window starting at a random time and recording for ``window_length`` time steps

        Parameters:
        ----------
        window_lengh:
            number of time steps to record
        n_people:
            number of random infected people to follow

        Returns:
        -------
            data frame summarising people's trajectories identified by their id
        """
        starting_id = randint(0, len(self.infections_df))
        starting_time = self.infections_df.index[starting_id]
        end_date = starting_time + datetime.timedelta(days=window_length)
        mask = (self.infections_df.index > starting_time) & (
            self.infections_df.index <= end_date
        )
        random_trajectories = self.infections_df.loc[mask]
        random_trajectories = random_trajectories.apply(pd.Series.explode)
        random_ids = sample(list(random_trajectories.infected_id.unique()), n_people)
        return [
            random_trajectories[random_trajectories["infected_id"] == random_id]
            for random_id in random_ids
        ]

    def load_infection_location(self) -> pd.DataFrame:
        """
        Load data frame with informtion on where did people get infected

        Returns
        -------
            data frame with infection locations, and average count of infections per group type
        """
        with h5py.File(self.file_path, "r", libver="latest", swmr=True) as f:
            locations = f["locations"]
            infection_location = []
            new_infected_ids = []
            for time_stamp in locations.keys():
                infection_location.append(
                    list(locations[time_stamp]["infection_location"][:].astype("U"))
                )
                new_infected_ids.append(
                    list(locations[time_stamp]["new_infected_ids"][:])
                )
            time_stamps = list(locations.keys())
        self.locations_df = pd.DataFrame(
            {
                "time_stamp": time_stamps,
                "location_id": infection_location,
                "new_infected_ids": new_infected_ids,
            }
        )
        self.locations_df["time_stamp"] = pd.to_datetime(
            self.locations_df["time_stamp"]
        )
        self.locations_df.set_index("time_stamp", inplace=True)
        self.locations_df = self.locations_df.resample("D").sum()
        self.locations_df["location"] = self.locations_df.apply(
            lambda x: [location_name.split("_")[0] for location_name in x.location_id],
            axis=1,
        )
        self.locations_df["super_areas"] = self.locations_df.apply(
            lambda x: self.super_areas[x.new_infected_ids], axis=1
        )

    def get_locations_infections(self, start_date=None, end_date=None,) -> pd.DataFrame:
        """
        Get a data frame with the number of infection happening at each type of place, within the given time
        period

        Parameters
        ----------
        start_date:
            first date to count
        end_date:
            last date to count
        """
        if start_date is None:
            start_date = self.infections_df.index.min()
        if end_date is None:
            end_date = self.infections_df.index.max()
        selected_dates = self.locations_df.loc[start_date:end_date]
        all_locations = selected_dates["location"].sum()
        return all_locations

    def get_location_infections_timeseries(
        self, start_date=None, end_date=None,
    ):
        """
        Get a data frame timeseries with the number of infection happening at each type of place, within the given time
        period

        Parameters
        ----------
        start_date:
            first date to count
        end_date:
            last date to count
        """
        if start_date is None:
            start_date = self.infections_df.index.min()
        if end_date is None:
            end_date = self.infections_df.index.max()
        selected_dates = self.locations_df.loc[start_date:end_date]

        all_locations = selected_dates.sum().location
        all_counts = selected_dates.sum().counts
        unique_locations = set(all_locations)

        time_series = pd.DataFrame(
            0, index=selected_dates.index, columns=unique_locations
        )
        for ts, row in selected_dates.iterrows():
            for location, count in zip(row["location"], row["counts"]):
                time_series.loc[ts, location] = count

        time_series["total"] = time_series.sum(axis=1)

        return time_series

    def load_hospital_characteristics(self) -> pd.DataFrame:
        """
        Get data frame with the coordinates of all hospitals in the world, and their number of beds

        Returns
        -------
            data frame indexed by the hospital id
        """
        with h5py.File(self.file_path, "r", libver="latest", swmr=True) as f:
            hospitals = f["hospitals"]
            coordinates = hospitals["coordinates"][:]
            n_beds = hospitals["n_beds"][:]
            n_icu_beds = hospitals["n_icu_beds"][:]
            trust_code = hospitals["trust_code"][:]
        hospitals_df = pd.DataFrame(
            {
                "longitude": coordinates[:, 1],
                "latitude": coordinates[:, 0],
                "n_beds": n_beds,
                "n_icu_beds": n_icu_beds,
                "trust_code": trust_code,
            }
        )
        hospitals_df["trust_code"] = hospitals_df["trust_code"].str.decode("utf-8")
        hospitals_df.index.rename("hospital_id")
        return hospitals_df

    def load_hospital_capacity(self) -> pd.DataFrame:
        """
        Load data on variation of number of patients in hospitals over time

        Returns
        -------
            data frame indexed by time stamp
        """
        with h5py.File(self.file_path, "r", libver="latest", swmr=True) as f:
            hospitals = f["hospitals"]
            hospital_ids = []
            n_patients = []
            n_patients_icu = []
            time_stamps = []
            for time_stamp in hospitals.keys():
                if time_stamp not in (
                    "coordinates",
                    "n_beds",
                    "n_icu_beds",
                    "trust_code",
                ):
                    hospital_ids.append(hospitals[time_stamp]["hospital_id"][:])
                    n_patients.append(hospitals[time_stamp]["n_patients"][:])
                    n_patients_icu.append(hospitals[time_stamp]["n_patients_icu"][:])
                    time_stamps.append(time_stamp)
        hospitals_df = pd.DataFrame(
            {
                "time_stamp": time_stamps,
                "id": hospital_ids,
                "n_patients": n_patients,
                "n_patients_icu": n_patients_icu,
            }
        )
        return hospitals_df.apply(pd.Series.explode)

    def get_r(self) -> pd.DataFrame:
        """
        Get R value as a function of time

        Returns
        -------
            data frame with R value, date as index
        """
        r_df = pd.DataFrame()
        r_df["value"] = self.infections_df.apply(
            lambda x: np.mean(x.n_secondary_infections[x.symptoms > 1]), axis=1
        )
        return r_df

    def repack_dict(
        self, hdf5_obj, output_dict, base_path, output_name=None, depth=0, max_depth=8
    ):

        if output_name is None:
            output_name = base_path.split("/")[-1]

        if depth > max_depth:
            output_dict[
                output_name
            ] = f"increase get_parameters max_depth, exceeded at max_depth={max_depth}"
            return None

        if isinstance(hdf5_obj[base_path], h5py.Dataset):
            output_dict[output_name] = hdf5_obj[base_path][()]
        elif isinstance(hdf5_obj[base_path], h5py.Group):
            output_dict[output_name] = {}
            for obj_name in hdf5_obj[base_path]:
                dset_path = f"{base_path}/{obj_name}"
                self.repack_dict(
                    hdf5_obj,
                    output_dict[output_name],
                    dset_path,
                    depth=depth + 1,
                    max_depth=max_depth,
                )  # Recursion!

    def get_parameters(self, parameters=["beta", "alpha_physical"], max_depth=8):
        if isinstance(parameters, list):
            parameters = {p: p for p in parameters}

        output_params = {}
        with h5py.File(self.file_path, "r", libver="latest", swmr=True) as f:
            for input_name, output_name in parameters.items():
                dset_path = f"parameters/{input_name}"
                self.repack_dict(
                    f,
                    output_params,
                    dset_path,
                    output_name=output_name,
                    depth=0,
                    max_depth=max_depth,
                )

        return output_params

    def save_run_summary(self,):
        world_df = self.world_summary()

        self.process_symptoms(self.infections_df, self.n_people)
