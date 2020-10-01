import h5py
import numpy as np
from random import sample, randint
import pandas as pd
import datetime
import functools
from itertools import chain
from pathlib import Path
from typing import List

from june.infection import SymptomTag
from june import paths
import time

class ReadLogger:
    def __init__(
        self,
        output_path: str = "results",
        root_output_file: str = "logger",
        n_processes: int = 1,
    ):
        """
        Read hdf5 file saved by the logger, and produce useful data frames

        Parameters
        ----------
        output_path:
            path to simulation's output
        root_output_path:
            name of file saved by simulation
        """
        self.output_path = Path(output_path)
        self.root_output_file = root_output_file
        self.n_processes = n_processes
        self.load_population_data()
        self.load_infected_data()

    def load_population_data(self):
        """
        Load data related to population (age, sex, ...)
        """
        
        n_people = []        
        ids = []
        ages = []
        sexes = []
        super_areas = []
        ethnicities = []
        socioeconomic_indices = []

        for rank in range(self.n_processes):
            with h5py.File(
                self.output_path / f"{self.root_output_file}.{rank}.hdf5",
                "r",
                libver="latest",
                swmr=True,
            ) as f:

                population = f["population"]
                n_people.append(population.attrs["n_people"])
                ids.append(population["id"][:])
                ages.append(population["age"][:])
                sexes.append(population["sex"][:])
                super_areas.append(
                    population['super_area'][:].astype("U13")
                )
                ethnicities.append(
                    population["ethnicity"][:]
                )
                socioeconomic_indices.append(
                    population["socioeconomic_index"][:]               
                )

        self.n_people = int(np.sum(n_people))
        self.ids = np.concatenate(ids)
        self.ages = np.concatenate(ages)
        self.sexes = np.concatenate(sexes)
        self.super_areas = np.concatenate(super_areas)
        self.ethnicites = np.concatenate(ethnicities)
        self.socioeconomic_indices = np.concatenate(socioeconomic_indices)

    def load_infected_data(self):

        for rank in range(self.n_processes):
            self._load_infected_data_for_rank(rank)

        self.ids = [0 for x in self.id_lists]
        self.symptoms = [0 for x in self.symptom_lists]
        for i,x in enumerate(self.id_lists):
            self.ids[i] = np.concatenate(x)
            self.id_lists[i] = 0
        for i,x in enumerate(self.symptom_lists):
            self.symptoms[i] = np.concatenate(x)
            self.symptom_lists[i] = 0

        self.infections_df = pd.DataFrame(
            {
                "time_stamp": self.time_stamps,
                "infected_id": self.ids,
                "symptoms": self.symptoms,
            }
        )
        self.infections_df.set_index("time_stamp", inplace=True)
        self.infections_df.index = pd.to_datetime(self.infections_df.index)

        self.infections_df["symptoms"] = self.infections_df.apply(
            lambda x: np.array(x.symptoms), axis=1
        )
        self.infections_df["infected_id"] = self.infections_df.apply(
            lambda x: np.array(x.infected_id), axis=1
        )
        self.start_date = min(self.infections_df.index)
        self.end_date = max(self.infections_df.index)

    def _load_infected_data_for_rank(self, rank: int):
        """
        Load data on infected people over time and convert to a list of data frames 
        ``self.infections_per_super_area``
        """
        infections_per_super_area = []
        with h5py.File(
            self.output_path / f"{self.root_output_file}.{rank}.hdf5",
            "r",
            libver="latest",
            swmr=True,
        ) as f:
            infections = f[f"infection"]
            if rank == 0:
                self.time_stamps = [key for key in infections]
                self.id_lists = [[] for time_stamp in self.time_stamps]
                self.symptom_lists = [[] for time_stamp in self.time_stamps]
            for i, time_stamp in enumerate(self.time_stamps):
                self.id_lists[i].append(infections[time_stamp]["id"][:])
                self.symptom_lists[i].append(infections[time_stamp]["symptoms"][:])
       

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
        df["daily_deaths"] = df[
            ["daily_deaths_home", "daily_deaths_hospital", "daily_deaths_icu"]
        ].sum(axis=1)
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
        df["daily_infections"] = (
            -df["current_susceptible"]
            .diff()
            .fillna(-df["current_infected"][0])
            .astype(int)
        )
        
        # filter rows that contain at least one hospitalised person
        hosp_df = symptoms_df.loc[df["current_hospitalised"] > 0]
        for ts, row in hosp_df.iterrows():
            mask = row["symptoms"] == SymptomTag.hospitalised
            for col, data in row.iteritems():
                if col in ("symptoms", "infected_id"):
                    hosp_df.loc[ts, col] = data[mask]
        flat_df = hosp_df[["symptoms", "infected_id"]].apply(lambda x: x.explode())
        unique, unique_indices = np.unique(
            flat_df["infected_id"].values, return_index=True
        )  # will only return the first index of each.
        flat_hospitalised_df = flat_df.iloc[unique_indices]
        df["daily_hospital_admissions"] = flat_hospitalised_df.groupby(
            flat_hospitalised_df.index
        ).size()
        df["daily_hospital_admissions"] = df["daily_hospital_admissions"].fillna(0.0)
        
        # filter rows that contain at least one ICU.
        icu_df = symptoms_df.loc[df["current_intensive_care"] > 0]
        for ts, row in icu_df.iterrows():
            mask = row["symptoms"] == SymptomTag.intensive_care
            for col, data in row.iteritems():
                if col in ("symptoms", "infected_id"):
                    hosp_df.loc[ts, col] = data[mask]
        flat_df = hosp_df[["symptoms", "infected_id"]].apply(lambda x: x.explode())
        unique, unique_indices = np.unique(
            flat_df["infected_id"].values, return_index=True
        )  # will only return the first index of each.
        flat_hospitalised_df = flat_df.iloc[unique_indices]
        df["daily_icu_admissions"] = flat_hospitalised_df.groupby(
            flat_hospitalised_df.index
        ).size()
        df["daily_icu_admissions"] = df["daily_icu_admissions"].fillna(0.0)

        return df

    def world_summary(self) -> pd.DataFrame:
        """
        Generate a summary at the world level, on how many people are recovered, dead, infected,
        susceptible, hospitalised or in intensive care, per time step.

        Returns
        -------
        A data frame whose index is the date recorded, and columns are number of recovered, 
        dead, infected...
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
        areas_df = []
        for area in np.unique(self.super_areas):
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
        infection_locations = []
        for rank in range(self.n_processes):
            self._load_infection_location_for_rank(rank=rank)
        self.infection_locations = [np.concatenate(x).tolist() for x in self.infection_location_lists]
        self.infection_locations_lists = []

        locations_df = pd.DataFrame(
            {
                "time_stamp": self.location_time_stamps,
                "location_id": self.infection_locations,
            }
        )
        locations_df["time_stamp"] = pd.to_datetime(locations_df["time_stamp"])
        locations_df.set_index("time_stamp", inplace=True)
        locations_df = locations_df.resample("D").sum()
        locations_df = locations_df[locations_df["location_id"] != 0]
        locations_df["location"] = locations_df.apply(
            lambda x: [
                ''.join(location_name.split("_")[:-1]) for location_name in x.location_id
            ],
            axis=1,
        )
        self.locations_df = locations_df


    def _load_infection_location_for_rank(self, rank: int) -> pd.DataFrame:
        """
        Load data frame with informtion on where did people get infected

        Returns
        -------
            data frame with infection locations, and average count of infections per group type
        """
        with h5py.File(
            self.output_path / f"{self.root_output_file}.{rank}.hdf5",
            "r",
            libver="latest",
            swmr=True,
        ) as f:
            locations = f[f"locations"]
            if rank == 0:
                self.location_time_stamps = list(locations.keys())
                self.infection_location_lists = [[] for time_stamp in self.location_time_stamps]
                for i, time_stamp in enumerate(locations.keys()):
                    self.infection_location_lists[i].append(
                        locations[time_stamp]["infection_location"][:].astype("U")
                    )
            else:
                for i, time_stamp in enumerate(locations.keys()):
                    # Will there ever be instance of no infections in a location in a domain?
                    if time_stamp not in locations.keys():
                        continue
                    self.infection_location_lists[i].append(
                        locations[time_stamp]['infection_location'][:].astype("U")
                    )

        
    def get_locations_infections(self, start_date=None, end_date=None,) -> pd.DataFrame:
        """
        Get a data frame with the number of infection happening at each type of place, 
        within the given time period

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
        coordinates, n_beds, n_icu_beds, trust_code = [], [], [], []
        with h5py.File(self.file_path, "r", libver="latest", swmr=True) as f:
            super_areas = [
                key for key in f.keys() if key not in ("population", "parameters")
            ]
            for super_area in super_areas:
                try:
                    hospitals = f[f"{super_area}/hospitals"]
                    coordinates += list(hospitals["coordinates"][:])
                    n_beds += list(hospitals["n_beds"][:])
                    n_icu_beds += list(hospitals["n_icu_beds"][:])
                    trust_code += list(hospitals["trust_code"][:])
                except KeyError:
                    continue
        coordinates = np.array(coordinates)
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
        hospitals_df = []
        with h5py.File(self.file_path, "r", libver="latest", swmr=True) as f:
            super_areas = [
                key for key in f.keys() if key not in ("population", "parameters")
            ]
            for super_area in super_areas:
                try:
                    hospitals = f[f"{super_area}/hospitals"]
                    hospital_ids, n_patients, n_patients_icu, time_stamps = (
                        [],
                        [],
                        [],
                        [],
                    )
                    for time_stamp in hospitals.keys():
                        if time_stamp not in (
                            "coordinates",
                            "n_beds",
                            "n_icu_beds",
                            "trust_code",
                        ):
                            hospital_ids.append(hospitals[time_stamp]["id"][:])
                            n_patients.append(hospitals[time_stamp]["n_patients"][:])
                            n_patients_icu.append(
                                hospitals[time_stamp]["n_patients_icu"][:]
                            )
                            time_stamps.append(time_stamp)
                    df = pd.DataFrame(
                        {
                            "time_stamp": time_stamps,
                            "id": hospital_ids,
                            "n_patients": n_patients,
                            "n_patients_icu": n_patients_icu,
                        }
                    )
                    df.set_index("time_stamp", inplace=True)
                    df.index = pd.to_datetime(df.index)
                    hospitals_df.append(df)
                except KeyError:
                    continue
        hospitals_df = functools.reduce(lambda a, b: a + b, hospitals_df)
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
        """
        Pack datesets into a (nested) dictionary.

        Parameters
        ----------
        hdf5_obj
            an open hdf5 object.
        output_dict
            an empty dictionary to store output data in
        base_path
            the path to start at
        """

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

    def get_parameters(self, parameters=None, max_depth=8):
        """
        Get the parameters which are stored in the logger.

        Parameters
        ----------
        parameters:
            which parameters to recover.
            default ["beta", "alpha_physical", "infection_seed", "asyptomatic_ratio"].
        max_depth:
            maximum nested dictionary depth to stop searching. Default = 8.
        Returns
            nested dictionary of parameters the simulation was run with.
        -------
        """
        defaults = [
            "beta", "alpha_physical", "infection_seed", "asymptomatic_ratio", "transmission_type"
        ]

        if parameters is None:
            parameters = defaults

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

    def get_config(self,):
        output_dict = {}
        with h5py.File(self.file_path, "r", libver="latest", swmr=True) as f:
            dset_path = f"config"
            self.repack_dict(
                f,
                output_dict,
                dset_path,
            )
        return output_dict["config"]

    def get_meta_info(self,parameters=None):
        meta_info = {}

        with h5py.File(self.file_path, "r", libver="latest", swmr=True) as f:
            self.repack_dict(f,output_dict=meta_info,base_path="meta")
        return meta_info["meta"]

    def run_summary(self,):
        super_area_df = self.super_area_summary()
        super_area_df["region"] = self.super_areas_to_region(
            super_area_df["super_area"].values
        )
        self.load_infection_location()
        flat_locations = self.locations_df[["location_id", "super_area"]].apply(
            lambda x: x.explode()
        )
        location_by_area = flat_locations.groupby(["super_area", flat_locations.index])[
            "location_id"
        ].apply(list)
        super_area_df = super_area_df.set_index(["super_area", super_area_df.index])
        super_area_df = super_area_df.merge(
            location_by_area, left_index=True, right_index=True, how="left",
        )
        super_area_df.reset_index(inplace=True)
        return super_area_df.set_index("time_stamp")


    def super_areas_to_region_mapping(self, super_areas, super_area_region_path=paths.data_path / 'input/geography/area_super_area_region.csv'):
        super_area_region = pd.read_csv(super_area_region_path)
        super_area_region = super_area_region.drop(columns='area').drop_duplicates()
        super_area_region.set_index('super_area', inplace=True)
        return super_area_region.loc[super_areas]['region'].values

    def region_summary(self) -> pd.DataFrame:
        """ 
        Generate a summary for regions, on how many people are recovered, dead, infected,
        susceptible, hospitalised or in intensive care, per time step.
        Returns
        -------
        A data frame whose index is the date recorded, and columns are regions, number of recovered,
        dead, infected...
        """
        regions = self.super_areas_to_region_mapping(self.super_areas)
        self.infections_df["regions"] = self.infections_df.apply(
          lambda x: regions[x.infected_id], axis=1
        )
        regions_df = []
        for region in np.unique(regions):
            region_df = pd.DataFrame()
            n_people_in_region = np.sum(regions == region)
            region_df["symptoms"] = self.infections_df.apply(
              lambda x: x.symptoms[x.regions == region], axis=1
            )
            region_df["infected_id"] = self.infections_df.apply(
              lambda x: x.infected_id[x.regions == region], axis=1
            )
            region_df = self.process_symptoms(region_df, n_people_in_region)
            region_df["region"] = region
            regions_df.append(region_df)
        return pd.concat(regions_df)
