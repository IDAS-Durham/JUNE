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
        n_observed_admissions: Optional[pd.DataFrame] = None,
        n_observed_deaths: Optional[pd.DataFrame] = None,
        msoa_region: Optional[pd.DataFrame] = None,
        regions = ['London']
    ):
        self.trajectories = trajectories
        self.msoa_region = msoa_region
        if super_areas is not None:
            self.population = self.get_population(super_areas, regions)
        self.health_index = health_index
        self.n_observed_admissions = n_observed_admissions[regions]
        self.n_observed_deaths = n_observed_deaths[regions]

    @classmethod
    def from_file(
        cls, super_areas, health_index, regions, config_path: str = default_config_path,
        msoa_region_filename: str = default_msoa_region_filename,
    ):
        with open(default_config_path) as f:
            trajectories = yaml.safe_load(f)["trajectories"]
        trajectories = [
            TrajectoryMaker.from_dict(trajectory) for trajectory in trajectories
        ]
        n_observed_admissions = pd.read_csv(
            paths.data_path / "processed/time_series/hospital_admissions_region.csv",
            index_col=0
        )
        n_observed_admissions.index = pd.to_datetime(n_observed_admissions.index)

        n_observed_deaths = pd.read_csv(
            paths.data_path / "processed/time_series/n_deaths_region.csv",
            index_col=0
        )
        n_observed_deaths.index = pd.to_datetime(n_observed_deaths.index)
        msoa_region = pd.read_csv(msoa_region_filename)[["super_area", "region"]]

        return Observed2Cases(
            trajectories=trajectories,
            super_areas=super_areas,
            regions=regions,
            health_index=health_index,
            n_observed_admissions=n_observed_admissions,
            n_observed_deaths=n_observed_deaths,
            msoa_region=msoa_region
        )

    def _filter_region(self, super_areas, region: str = "North East") -> List["SuperArea"]:
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
        else:
            msoa_region_filtered = self.msoa_region[self.msoa_region.region == region]
        filter_region = list(
            map(
                lambda x: x in msoa_region_filtered["super_area"].values,
                [super_area.name for super_area in super_areas.members],
            )
        )
        return np.array(super_areas.members)[filter_region]
 

    def get_population(self, super_areas, regions):
        population = dict()
        for region in regions:
            population[region] = self.get_population_for_region(super_areas, region)
        return population

    def get_population_for_region(self, super_areas, region):
        super_in_region = self._filter_region(super_areas, region)
        print('super in region = ', super_in_region)
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
        age_dict = {'m': defaultdict(int), 'f': defaultdict(int)}
        for person in self.population[region]:
            age_dict[person.sex][person.age] += 1
        return age_dict

    def get_health_index_by_age_and_sex(self):
        health_dict = {'m': defaultdict(int), 'f': defaultdict(int)}
        for sex in ('m', 'f'):
            for age in np.arange(100):
                health_dict[sex][age] = self.health_index(Person(sex=sex, age=age))
        return health_dict

    def get_avg_rate_for_symptoms(self, symptoms_tags, region):
        # TODO: do only for one person per age/sex and multiply by number of people
        avg_rates = 0
        age_dict = self.get_age_structure(region)
        health_dict = self.get_health_index_by_age_and_sex()
        for sex in ('m', 'f'):
            for age in np.arange(100):
                avg_rates += np.diff(np.append(health_dict[sex][age], 1))*age_dict[sex][age]
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

    def cases_from_observation(self, n_observed_df, time_to_get_there, avg_rates):
        n_initial_cases = []
        for index, n_observed in n_observed_df.iteritems():
            date = index - timedelta(days=time_to_get_there)
            n_cases = self.get_n_cases_from_observed(n_observed, avg_rates)
            n_initial_cases.append((date, round(n_cases)))
        return pd.DataFrame(n_initial_cases, columns=['date',
                                        'n_cases'])
