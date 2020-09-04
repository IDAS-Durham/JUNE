import pandas as pd
from typing import List, Optional
import yaml
import numpy as np
from datetime import timedelta
from collections import defaultdict, Counter
from scipy.ndimage import gaussian_filter1d

from june.infection.symptom_tag import SymptomTag
from june.demography import Person
from june.infection.trajectory_maker import TrajectoryMaker
from june import paths

default_config_path = paths.configs_path / "defaults/symptoms/trajectories.yaml"
default_super_area_region_filename = (
    paths.data_path / "input/geography/area_super_area_region.csv"
)


class Observed2Cases:
    def __init__(
        self,
        age_per_area_df,
        female_fraction_per_area_df,
        health_index_generator=None,
        trajectories=None,
        n_observed_deaths: Optional[pd.DataFrame] = None,
        area_super_region_df: Optional[pd.DataFrame] = None,
        smoothing=False,
    ):
        self.area_super_region_df = area_super_region_df
        self.age_per_area_df = age_per_area_df
        (
            self.females_per_age_region_df,
            self.males_per_age_region_df,
        ) = self.generate_demography_dfs_by_region(
            age_per_area_df=age_per_area_df,
            female_fraction_per_area_df=female_fraction_per_area_df,
        )
        self.trajectories = trajectories
        self.health_index_generator = health_index_generator
        self.regions = self.area_super_region_df["region"].unique()
        if smoothing:
            n_observed_deaths = self._smooth_time_series(n_observed_deaths)

    @classmethod
    def from_file(
        cls,
        population,
        health_index_generator,
        config_path: str = default_config_path,
        super_area_region_filename: str = default_super_area_region_filename,
        smoothing=False,
    ):
        with open(default_config_path) as f:
            trajectories = yaml.safe_load(f)["trajectories"]
        trajectories = [
            TrajectoryMaker.from_dict(trajectory) for trajectory in trajectories
        ]
        n_observed_deaths = pd.read_csv(
            paths.data_path / "covid_real_data/n_deaths_region.csv", index_col=0
        )
        n_observed_deaths.index = pd.to_datetime(n_observed_deaths.index)
        super_area_region_mapping = pd.read_csv(super_area_region_filename)[
            ["super_area", "region"]
        ]

        return Observed2Cases(
            trajectories=trajectories,
            population=population,
            health_index_generator=health_index_generator,
            n_observed_deaths=n_observed_deaths,
            super_area_region_mapping=super_area_region_mapping,
            smoothing=smoothing,
        )

    def aggregate_areas_by_region(self, df_per_area):
        return (
            pd.merge(
                df_per_area,
                self.area_super_region_df.drop(columns="super_area"),
                left_index=True,
                right_index=True,
            )
            .groupby("region")
            .sum()
        )

    def generate_demography_dfs_by_region(
        self, age_per_area_df, female_fraction_per_area_df,
    ):
        sex_bins = list(map(int, female_fraction_per_area_df.columns))
        females_per_age_area_df = age_per_area_df.apply(
            lambda x: x
            * female_fraction_per_area_df[
                female_fraction_per_area_df.columns[
                    np.digitize(int(x.name), bins=sex_bins) - 1
                ]
            ]
        ).astype("int")
        males_per_age_area_df = age_per_area_df - females_per_age_area_df
        females_per_age_region_df = self.aggregate_areas_by_region(
            females_per_age_area_df
        )
        males_per_age_region_df = self.aggregate_areas_by_region(males_per_age_area_df)
        return females_per_age_region_df, males_per_age_region_df

    def get_all_rates_per_age_sex(self,):
        rates_dict = {"m": defaultdict(int), "f": defaultdict(int)}
        for sex in ("m", "f"):
            for age in np.arange(100):
                rates_dict[sex][age] = np.diff(
                    self.health_index_generator(Person(sex=sex, age=age)),
                    prepend=0.0,
                    append=1.0,
                )
        return rates_dict

    def get_rates_weighted_by_age_sex_per_region(self, rates_dict, symptoms_tags):
        idx_rates = [getattr(SymptomTag, tag) for tag in symptoms_tags]
        avg_rates = {}
        for region in self.regions:
            avg_rate_region = 0
            for age in np.arange(100):
                avg_rate_region += (
                    rates_dict["f"][age][idx_rates]
                    * self.females_per_age_region_df.loc[region][str(age)]
                )
                avg_rate_region += (
                    rates_dict["m"][age][idx_rates]
                    * self.males_per_age_region_df.loc[region][str(age)]
                )
            n_people_region = (
                self.females_per_age_region_df.loc[region].sum()
                + self.males_per_age_region_df.loc[region].sum()
            )
            avg_rates[region] = avg_rate_region / n_people_region
        return avg_rates

    def get_expected_cases_given_observed(self, n_observed, avg_rates):
        avg_rate = sum(avg_rates)
        return round(n_observed / avg_rate)

    def cases_from_observation_per_region(
        self, n_observed_df, time_to_get_there, avg_rates_per_region
    ):
        n_cases_per_region_df = n_observed_df.apply(
            lambda x: self.get_expected_cases_given_observed(
                x, avg_rates_per_region[x.name]
            )
        )
        n_cases_per_region_df.index = n_observed_df.index - timedelta(
            days=round(time_to_get_there)
        )
        return n_cases_per_region_df

    def get_super_area_weights(self,):
        people_per_super_area = (
            pd.merge(
                self.age_per_area_df.sum(axis=1).to_frame("n_people"),
                self.area_super_region_df.drop(columns="region"),
                left_index=True,
                right_index=True,
            )
            .groupby("super_area")
            .sum()
        )
        people_per_super_aera_and_region = pd.merge(
            people_per_super_area,
            self.area_super_region_df.drop_duplicates().set_index("super_area"),
            left_index=True,
            right_index=True,
            how="left",
        )
        people_per_region = people_per_super_aera_and_region.groupby("region").sum()[
            "n_people"
        ]
        people_per_super_aera_and_region[
            "weights"
        ] = people_per_super_aera_and_region.apply(
            lambda x: x.n_people / people_per_region.loc[x.region], axis=1
        )
        return people_per_super_aera_and_region[["weights", "region"]]

    def convert_regional_cases_to_super_area(self, n_cases_per_region_df):
        n_cases_per_super_area_df = pd.DataFrame(
            0,
            index=n_cases_per_region_df.index,
            columns=self.area_super_region_df["super_area"].unique(),
        )
        super_area_weights = self.get_super_area_weights()
        super_area_cases = []
        for region in n_cases_per_region_df.columns:
            super_area_weights_for_region = super_area_weights[
                super_area_weights["region"] == region
            ]
            for date, n_cases in n_cases_per_region_df[region].iteritems():
                chosen_super_areas = np.random.choice(
                    list(super_area_weights_for_region.index),
                    replace=True,
                    size=round(n_cases),
                    p=super_area_weights_for_region["weights"],
                )
                n_cases_super_area = Counter(chosen_super_areas)
                n_cases_per_super_area_df.loc[
                    date, list(n_cases_super_area.keys())
                ] = n_cases_super_area.values()
        return n_cases_per_super_area_df

    def _smooth_time_series(self, time_series_df):
        return time_series_df.apply(lambda x: gaussian_filter1d(x, sigma=2))

    def filter_trajectories(
        self, trajectories, symptoms_to_keep=("dead_hospital", "dead_icu")
    ):
        filtered_trajectories = []
        for trajectory in trajectories:
            symptom_tags = [stage.symptoms_tag.name for stage in trajectory.stages]
            if set(symptom_tags).intersection(set(symptoms_to_keep)):
                filtered_trajectories.append(trajectory)
        return filtered_trajectories

    def get_median_completion_time(self, stage):
        if hasattr(stage.completion_time, "distribution"):
            return stage.completion_time.distribution.median()
        else:
            return stage.completion_time.value

    def get_time_it_takes_to_symptoms(self, trajectories, symptoms_tags):
        time_to_symptoms = []
        for trajectory in trajectories:
            time = 0
            for stage in trajectory.stages:
                if stage.symptoms_tag.name in symptoms_tags:
                    break
                time += self.get_median_completion_time(stage)
            time_to_symptoms.append(time)
        return time_to_symptoms

    def get_avg_time_to_symptoms(
        self, trajectories, avg_rate_for_symptoms, symptoms_tags
    ):
        times_to_symptoms = self.get_time_it_takes_to_symptoms(
            trajectories, symptoms_tags=symptoms_tags
        )
        return sum(avg_rate_for_symptoms * times_to_symptoms) / sum(
            avg_rate_for_symptoms
        )
        
