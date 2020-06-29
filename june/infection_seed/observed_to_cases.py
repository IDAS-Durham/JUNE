import pandas as pd
from typing import List, Tuple, Optional
import yaml
import numpy as np
from datetime import timedelta
from collections import defaultdict

from june.infection.symptom_tag import SymptomTag
from june.demography import Person
from june.infection.trajectory_maker import TrajectoryMaker
from june import paths

default_config_path = paths.configs_path / "defaults/symptoms/trajectories.yaml"
default_msoa_region_filename = (
    paths.data_path / "input/geography/area_super_area_region.csv"
)


class Observed2Cases:
    def __init__(
        self,
        trajectories=None,
        super_areas=None,
        health_index=None,
        n_observed_deaths: Optional[pd.DataFrame] = None,
        msoa_region: Optional[pd.DataFrame] = None,
        regions: Optional[List[str]]=None,
    ):
        self.trajectories = trajectories
        self.msoa_region = msoa_region
        self.super_areas = super_areas
        self.all_regions = n_observed_deaths.columns
        if super_areas is not None:
            self.regions = self.find_regions_for_super_areas(super_areas)
            self.population = self.get_population(super_areas, self.regions)
        self.n_observed_deaths = n_observed_deaths[self.regions]
        self.health_index = health_index

    @classmethod
    def from_file(
        cls,
        super_areas,
        health_index,
        config_path: str = default_config_path,
        msoa_region_filename: str = default_msoa_region_filename,
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
        msoa_region = pd.read_csv(msoa_region_filename)[["super_area", "region"]]

        return Observed2Cases(
            trajectories=trajectories,
            super_areas=super_areas,
            health_index=health_index,
            n_observed_deaths=n_observed_deaths,
            msoa_region=msoa_region,
        )

    def _filter_region(
        self, super_areas, region: str = "North East"
    ) -> List["SuperArea"]:
        """
        Given a region, return a list of super areas belonging to that region

        Parameters
        ----------
        region:
            name of the region
        """
        if "North East" in region:
            msoa_region_filtered = self.msoa_region[
                (self.msoa_region.region == "North East")
                | (self.msoa_region.region == "Yorkshire and The Humber")
            ]
        elif "Midlands" in region:
            msoa_region_filtered = self.msoa_region[
                (self.msoa_region.region == "West Midlands")
                | (self.msoa_region.region == "East Midlands")
            ]

        else:
            msoa_region_filtered = self.msoa_region[self.msoa_region.region == region]
        filter_region = list(
            map(
                lambda x: x in msoa_region_filtered["super_area"].values,
                [super_area.name for super_area in super_areas.members],
            )
        )
        return np.array(super_areas.members)[filter_region]

    def find_regions_for_super_areas(self, super_areas):
        regions = []
        for region in self.all_regions:
            if len(self._filter_region(super_areas,region)) > 0:
                regions.append(region)
        return regions

    def get_population(self, super_areas, regions):
        population = dict()
        for region in regions:
            population[region] = self.get_population_for_region(super_areas, region)
        return population

    def get_population_for_region(self, super_areas, region):
        super_in_region = self._filter_region(super_areas, region)
        population = []
        for super_area in super_in_region:
            population += super_area.people
        return population

    def filter_trajectories(
        self, trajectories, symptoms_to_keep=("dead_hospital", "dead_icu")
    ):
        filtered_trajectories = []
        for trajectory in trajectories:
            symptom_tags = [stage.symptoms_tag.name for stage in trajectory.stages]
            if set(symptom_tags).intersection(set(symptoms_to_keep)):
                filtered_trajectories.append(trajectory)
        return filtered_trajectories

    def get_mean_completion_time(self, stage):
        if hasattr(stage.completion_time, "distribution"):
            return stage.completion_time.distribution.mean()
        else:
            return stage.completion_time.value

    def get_time_it_takes_to_symptoms(self, trajectories, symptoms_tags):
        time_to_symptoms = []
        for trajectory in trajectories:
            time = 0
            for stage in trajectory.stages:
                if stage.symptoms_tag.name in symptoms_tags:
                    break
                time += self.get_mean_completion_time(stage)
            time_to_symptoms.append(time)
        return time_to_symptoms

    def get_age_structure(self, region):
        age_dict = {"m": defaultdict(int), "f": defaultdict(int)}
        for person in self.population[region]:
            age_dict[person.sex][person.age] += 1
        return age_dict

    def get_health_index_by_age_and_sex(self):
        health_dict = {"m": defaultdict(int), "f": defaultdict(int)}
        for sex in ("m", "f"):
            for age in np.arange(100):
                health_dict[sex][age] = self.health_index(Person(sex=sex, age=age))
        return health_dict

    def get_avg_rate_for_symptoms(self, symptoms_tags, region):
        avg_rates = 0
        age_dict = self.get_age_structure(region)
        health_dict = self.get_health_index_by_age_and_sex()
        for sex in ("m", "f"):
            for age in np.arange(100):
                avg_rates += (
                    np.diff(np.append(health_dict[sex][age], 1)) * age_dict[sex][age]
                )
        idx = [getattr(SymptomTag, tag) - 1 for tag in symptoms_tags]
        return avg_rates[idx] / len(self.population[region])

    def get_avg_time_to_symptoms(
        self, trajectories, avg_rate_for_symptoms, symptoms_tags
    ):
        times_to_symptoms = self.get_time_it_takes_to_symptoms(
            trajectories, symptoms_tags=symptoms_tags
        )
        return sum(avg_rate_for_symptoms * times_to_symptoms) / sum(
            avg_rate_for_symptoms
        )

    def get_n_cases_from_observed(self, n_observed, avg_rates):
        avg_rate = sum(avg_rates)
        return n_observed / avg_rate

    def cases_from_observation(
        self, n_observed_df, time_to_get_there, avg_rates, region
    ):
        n_initial_cases = []
        for index, n_observed in n_observed_df.iterrows():
            date = index - timedelta(days=round(time_to_get_there))
            n_cases = self.get_n_cases_from_observed(n_observed[region], avg_rates)
            n_initial_cases.append((date, round(n_cases)))
        n_cases_df = pd.DataFrame(n_initial_cases, columns=["date", region])
        n_cases_df.set_index('date', inplace=True)
        n_cases_df.index = pd.to_datetime(n_cases_df.index)
        n_cases_df.index = n_cases_df.index.round('D')
        return n_cases_df

    def cases_from_deaths_for_region(self, region):
        dead_trajectories = self.filter_trajectories(self.trajectories)
        avg_rates = self.get_avg_rate_for_symptoms(
            symptoms_tags=("dead_icu", "dead_hospital"), region=region
        )
        time_to_death = self.get_avg_time_to_symptoms(
            dead_trajectories, avg_rates, symptoms_tags=("dead_icu", "dead_hospital")
        )
        return self.cases_from_observation(
            self.n_observed_deaths, time_to_death, avg_rates, region=region
        )

    def cases_from_deaths(self):
        cases_dfs = []
        for region in self.regions:
            cases_dfs.append(self.cases_from_deaths_for_region(region))
        return pd.concat(cases_dfs, axis=1)


    def cases_from_admissions_for_region(self, region):
        hospitalised_trajectories = self.filter_trajectories(self.trajectories)
        avg_rates = self.get_avg_rate_for_symptoms(
            symptoms_tags=(
                "hospitalised",
                "intensive_care",
                "dead_icu",
                "dead_hospital",
            ),
            region=region,
        )
        time_to_hospital = self.get_avg_time_to_symptoms(
            hospitalised_trajectories,
            avg_rates,
            symptoms_tags=("hospitalised", "intensive_care"),
        )
        return self.cases_from_observation(
            self.n_observed_deaths, time_to_hospital, avg_rates, region=region
        )
