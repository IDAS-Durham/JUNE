import pandas as pd
import yaml
import numpy as np
from datetime import timedelta
from typing import List, Optional, Tuple, Union, Dict
from collections import defaultdict, Counter
from scipy.ndimage import gaussian_filter1d

from june import paths
from june.demography import Person
from june.epidemiology.infection.symptom_tag import SymptomTag
from june.epidemiology.infection.trajectory_maker import TrajectoryMaker

default_trajectories_path = paths.configs_path / "defaults/epidemiology/infection/symptoms/trajectories.yaml"
default_area_super_region_path = (
    paths.data_path / "input/geography/area_super_area_region.csv"
)
default_observed_deaths_path = (
    paths.data_path / "input/infection_seed/hospital_deaths_per_region_per_date.csv"
)
default_age_per_area_path = (
    paths.data_path / "input/demography/age_structure_single_year.csv"
)
default_female_fraction_per_area_path = (
    paths.data_path / "input/demography/female_ratios_per_age_bin.csv"
)


class Observed2Cases:
    def __init__(
        self,
        age_per_area_df: pd.DataFrame,
        female_fraction_per_area_df: pd.DataFrame,
        regional_infections_per_hundred_thousand=100,
        health_index_generator: "HealthIndexGenerator" = None,
        symptoms_trajectories: Optional["TrajectoryMaker"] = None,
        n_observed_deaths: Optional[pd.DataFrame] = None,
        area_super_region_df: Optional[pd.DataFrame] = None,
        smoothing=False,
    ):
        """
        Class to convert observed deaths over time into predicted number of latent cases
        over time, use for the seed of the infection.
        It reads population data, to compute average death rates for a particular region,
        timings from config file estimate the median time it takes for someone infected to
        die in hospital, and the health index to obtain the death rate as a function of
        age and sex.

        Parameters
        ----------
        age_per_area_df:
            data frame with the age distribution per area, to compute the weighted death rate
        female_fraction_per_area_df:
            data frame with the fraction of females per area as a function of age to compute
            the weighted death rate
        health_index_generator:
            generator of the health index to compute death_rate(age,sex)
        symptoms_trajectories:
            used to read the trajectory config file and compute the
            median time it takes to die in hospital
        n_observed_deaths:
            time series with the number of observed deaths per region
        area_super_region_df:
            df with area, super_area, region mapping
        smoothing:
            whether to smooth the observed deaths time series before computing
            the expected number of cases (therefore the estimates becomes less
            dependent on spikes in the data)
        """
        self.regional_infections_per_hundred_thousand = (
            regional_infections_per_hundred_thousand
        )
        self.area_super_region_df = area_super_region_df
        self.age_per_area_df = age_per_area_df
        (
            self.females_per_age_region_df,
            self.males_per_age_region_df,
        ) = self.aggregate_age_sex_dfs_by_region(
            age_per_area_df=age_per_area_df,
            female_fraction_per_area_df=female_fraction_per_area_df,
        )
        self.symptoms_trajectories = symptoms_trajectories
        self.health_index_generator = health_index_generator
        self.regions = self.area_super_region_df["region"].unique()
        # TODO: this are particularities of England that should not be here.
        if (
            n_observed_deaths is not None
            and "East Of England" in n_observed_deaths.columns
        ):
            n_observed_deaths = n_observed_deaths.rename(
                columns={"East Of England": "East of England"}
            )
        if smoothing:
            n_observed_deaths = self._smooth_time_series(n_observed_deaths)
        self.n_observed_deaths = n_observed_deaths

    @classmethod
    def from_file(
        cls,
        health_index_generator,
        regional_infections_per_hundred_thousand=100,
        age_per_area_path: str = default_age_per_area_path,
        female_fraction_per_area_path: str = default_female_fraction_per_area_path,
        trajectories_path: str = default_trajectories_path,
        observed_deaths_path: str = default_observed_deaths_path,
        area_super_region_path: str = default_area_super_region_path,
        smoothing=False,
    ) -> "Observed2Cases":
        """
        Creates class from paths to data

        Parameters
        ----------
        health_index_generator:
            generator of the health index to compute death_rate(age,sex)
        age_per_area_path:
            path to data with number of people of a given age by area
        female_fraction_per_area_df:
            path to data with fraction of people that are female by area and age bin
        trajectories_path:
            path to config file with possible symptoms trajectories and their timings
        observed_deaths_path:
            path to time series of observed deaths over time
        area_super_region_path:
            path to data on area, super_area, region mapping
        smoothing:
            whether to smooth the observed deaths time series before computing
            the expected number of cases (therefore the estimates becomes less
            dependent on spikes in the data)

        Returns
        -------
        Instance of Observed2Cases
        """
        age_per_area_df = pd.read_csv(age_per_area_path, index_col=0)
        female_fraction_per_area_df = pd.read_csv(
            female_fraction_per_area_path, index_col=0
        )
        with open(trajectories_path) as f:
            symptoms_trajectories = yaml.safe_load(f)["trajectories"]
        symptoms_trajectories = [
            TrajectoryMaker.from_dict(trajectory)
            for trajectory in symptoms_trajectories
        ]
        n_observed_deaths = pd.read_csv(observed_deaths_path, index_col=0)
        n_observed_deaths.index = pd.to_datetime(n_observed_deaths.index)
        area_super_region_df = pd.read_csv(area_super_region_path, index_col=0)
        # Combine regions as in deaths dataset
        # TODO: do this outside here for generality
        area_super_region_df = area_super_region_df.replace(
            {
                "region": {
                    "West Midlands": "Midlands",
                    "East Midlands": "Midlands",
                    "North East": "North East And Yorkshire",
                    "Yorkshire and The Humber": "North East And Yorkshire",
                }
            }
        )
        return cls(
            regional_infections_per_hundred_thousand=regional_infections_per_hundred_thousand,
            age_per_area_df=age_per_area_df,
            female_fraction_per_area_df=female_fraction_per_area_df,
            health_index_generator=health_index_generator,
            symptoms_trajectories=symptoms_trajectories,
            n_observed_deaths=n_observed_deaths,
            area_super_region_df=area_super_region_df,
            smoothing=smoothing,
        )

    def aggregate_areas_by_region(self, df_per_area: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregates an area dataframe into a region dataframe

        Parameters
        ----------
        df_per_area:
            data frame indexed by area

        Returns
        -------
        """
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

    def aggregate_age_sex_dfs_by_region(
        self,
        age_per_area_df: pd.DataFrame,
        female_fraction_per_area_df: pd.DataFrame,
    ) -> (pd.DataFrame, pd.DataFrame):
        """
        Combines the age per area dataframe and female fraction per area to
        create two data frames with numbers of females by age per region, and
        numbers of males by age per region

        Parameters
        ----------
        age_per_area_df:
            data frame with the number of people with a certain age per area
        female_fraction_per_area_df:
            fraction of those that are females per area and age bin

        Returns
        -------
        females_per_age_region_df:
            number of females as a function of age per region
        males_per_age_region_df:
            number of males as a function of age per region
        """
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

    def get_symptoms_rates_per_age_sex(
        self,
    ) -> dict:
        """
        Computes the rates of ending up with certain SymptomTag for all
        ages and sex.

        Returns
        -------
        dictionary with rates of symptoms (fate) as a function of age and sex
        """
        symptoms_rates_dict = {"m": defaultdict(int), "f": defaultdict(int)}
        for sex in ("m", "f"):
            for age in np.arange(100):
                symptoms_rates_dict[sex][age] = np.diff(
                    self.health_index_generator(Person(sex=sex, age=age), infection_id=None),
                    prepend=0.0,
                    append=1.0,
                )  # need np.diff because health index is cummulative
        return symptoms_rates_dict

    def weight_rates_by_age_sex_per_region(
        self, symptoms_rates_dict: dict, symptoms_tags: List["SymptomTag"]
    ) -> List[float]:
        """
        Get the weighted average by age and sex of symptoms rates for symptoms in symptoms_tags.
        For example to get the weighted average death rate per region,
        select symptoms_tags = ('dead_hospital', 'dead_icu', 'dead_home')

        Parameters
        ----------
        symtpoms_rates_dict:
            dictionary with rates for all the possible final symptoms, indexed by sex and age.
        symptoms_tags:
            final symptoms to keep
        Returns
        -------
        List of weighted rates for symptoms in ```symptoms_tags``` (ordered in the same way!!)
        """
        idx_symptoms_to_keep = [getattr(SymptomTag, tag) for tag in symptoms_tags]
        weighted_rates = {}
        for region in self.regions:
            weighted_rates_region = 0
            for age in np.arange(100):
                weighted_rates_region += (
                    symptoms_rates_dict["f"][age][idx_symptoms_to_keep]
                    * self.females_per_age_region_df.loc[region][str(age)]
                )
                weighted_rates_region += (
                    symptoms_rates_dict["m"][age][idx_symptoms_to_keep]
                    * self.males_per_age_region_df.loc[region][str(age)]
                )
            n_people_region = (
                self.females_per_age_region_df.loc[region].sum()
                + self.males_per_age_region_df.loc[region].sum()
            )
            weighted_rates[region] = weighted_rates_region / n_people_region
        return weighted_rates

    def get_latent_cases_from_observed(self, n_observed: int, avg_rates: List) -> int:
        """
        Given a number of observed cases, such as observed deaths or observed hospital
        admissions, this function converts it into number of latent cases necessary to
        produce such an observation.

        Parameters
        ----------
        n_observed:
            observed number of cases (such as deaths or hospital admissions)
        avg_rates:
            average rates to produce the observed cases, such as average death rate or average
            admission rates. It is a list, since we might want to look at, for instance,
            death rate, which is a combination of deat_home, deat_hospital, dead_icu rates.
        Returns
        -------
        Number of latent cases
        """
        avg_rate = sum(avg_rates)
        return round(n_observed / avg_rate)

    def get_latent_cases_per_region(
        self,
        n_observed_df: pd.DataFrame,
        time_to_get_symptoms: int,
        avg_rates_per_region: dict,
    ) -> pd.DataFrame:
        """
        Converts observed cases per region into latent cases per region.

        Parameters
        ----------
        n_observed_df:
            time series of the observed cases
        time_to_get_symptoms:
            days it takes form infection to the symptoms of interest (such as time to death)
        avg_rates_per_region:
            average probability to get those symptoms per region

        Returns
        -------
        n_cases_per_region_df:
            number of latent cases per region time series
        """
        n_cases_per_region_df = n_observed_df.apply(
            lambda x: self.get_latent_cases_from_observed(
                x, avg_rates_per_region[x.name]
            )
        )
        n_cases_per_region_df.index = n_observed_df.index - timedelta(
            days=time_to_get_symptoms
        )
        return n_cases_per_region_df

    def get_super_area_population_weights(
        self,
    ) -> pd.DataFrame:
        """
        Compute the weight in population that a super area has over its whole region, used
        to convert regional cases to cases by super area by population density

        Returns
        -------
        data frame indexed by super area, with weights and region
        """
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

    def limit_cases_per_region(self, n_cases_per_region_df, starting_date="2020-02-24"):
        people_per_region = self.females_per_age_region_df.sum(
            axis=1
        ) + self.males_per_age_region_df.sum(axis=1)
        n_cases_per_region_df = n_cases_per_region_df.loc[starting_date:]
        cummulative_infections_hundred_thousand = (
            n_cases_per_region_df.cumsum() / people_per_region * 100_000
        )
        regional_series = []
        for region in n_cases_per_region_df.columns:
            regional_index = np.searchsorted(
                cummulative_infections_hundred_thousand[region].values,
                self.regional_infections_per_hundred_thousand,
            )
            regional_cases_to_seed = n_cases_per_region_df[region].iloc[
                : regional_index + 1
            ]
            target_cases = (
                self.regional_infections_per_hundred_thousand
                * people_per_region.loc[region]
                / 100_000
            )
            remaining_cases = np.round(
                max(0, target_cases - regional_cases_to_seed.iloc[:-1].sum())
            )
            regional_cases_to_seed.iloc[-1] = remaining_cases
            regional_series.append(regional_cases_to_seed)
        return pd.concat(regional_series, axis=1).fillna(0.0)

    def convert_regional_cases_to_super_area(
        self,
        n_cases_per_region_df: pd.DataFrame,
        starting_date: str,
    ) -> pd.DataFrame:
        """
        Converts regional cases to cases by super area by weighting each super area
        within the region according to its population

        Parameters
        ----------
        n_cases_per_region_df:
            data frame with the number of cases by region, indexed by date
        dates:
            dates to select (it can be a dictinary with different dates for different regions

        Returns
        -------
        data frame with the number of cases by super area, indexed by date
        """
        n_cases_per_region_df = self.limit_cases_per_region(
            n_cases_per_region_df=n_cases_per_region_df,
            starting_date=starting_date,
        )
        n_cases_per_super_area_df = pd.DataFrame(
            0,
            index=n_cases_per_region_df.index,
            columns=self.area_super_region_df["super_area"].unique(),
        )
        super_area_weights = self.get_super_area_population_weights()
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

    def _smooth_time_series(self, time_series_df: pd.DataFrame) -> pd.DataFrame:
        """
        Smooth a time series by applying a gaussian filter in 1d

        Parameters
        ----------
        time_series_df:
            df with time as index

        Returns
        -------
        smoothed time series df
        """
        return time_series_df.apply(lambda x: gaussian_filter1d(x, sigma=2))

    def filter_symptoms_trajectories(
        self,
        symptoms_trajectories: List["TrajectoryMaker"],
        symptoms_to_keep: Tuple[str] = ("dead_hospital", "dead_icu"),
    ) -> List["TrajectoryMaker"]:
        """
        Filter all symptoms trajectories to obtain only the ones that contain given symtpoms
        in ```symptoms_to_keep```

        Parameters
        ----------
        symptoms_trajectories:
            list of all symptoms trajectories
        symptoms_to_keep:
            tuple of strings containing the desired symptoms for which to find trajectories

        Returns
        -------
        trajectories containing ```symptoms_to_keep```
        """
        filtered_trajectories = []
        for trajectory in symptoms_trajectories:
            symptom_tags = [stage.symptoms_tag.name for stage in trajectory.stages]
            if set(symptom_tags).intersection(set(symptoms_to_keep)):
                filtered_trajectories.append(trajectory)
        return filtered_trajectories

    def get_median_completion_time(self, stage: "Stage") -> float:
        """
        Get median completion time of a stage, from its distribution

        Parameters
        ----------
            stage:
                given stage in trajectory
        Returns
        -------
        Median time spent in stage
        """
        if hasattr(stage.completion_time, "distribution"):
            return stage.completion_time.distribution.median()
        else:
            return stage.completion_time.value

    def get_time_it_takes_to_symptoms(
        self, symptoms_trajectories: List["TrajectoryMaker"], symptoms_tags: List[str]
    ):
        """
        Compute the median time it takes to get certain symptoms in ```symptoms_tags```, such as death or hospital
        admission.

        Parameters
        ----------
        symptoms_trajectories:
            list of symptoms trajectories
        symptoms_tags:
            symptoms tags for the symptoms of interest
        """
        time_to_symptoms = []
        for trajectory in symptoms_trajectories:
            time = 0
            for stage in trajectory.stages:
                if stage.symptoms_tag.name in symptoms_tags:
                    break
                time += self.get_median_completion_time(stage)
            time_to_symptoms.append(time)
        return time_to_symptoms

    def get_weighted_time_to_symptoms(
        self,
        symptoms_trajectories: List["TrajectoryMaker"],
        avg_rate_for_symptoms: List["float"],
        symptoms_tags: List[str],
    ) -> float:
        """
        Get the time it takes to get certain symptoms weighted by population. For instance,
        when computing the death rate, more people die in hospital than in icu,
        therefore the median time to die in hospital gets weighted more than the median time
        to die in icu.

        Parameters
        ----------
        symptoms_trajectories:
            trajectories for symptoms that include the symptoms of interest
        avg_rate_for_symptoms:
            list containing the average rate for certain symptoms given in ```symptoms tags```.
            WARNING: should be in the same order
        symptoms_tags:
            tags of the symptoms for which we want to know the median time

        Returns
        -------
        Weighted median time to symptoms

        """
        times_to_symptoms = self.get_time_it_takes_to_symptoms(
            symptoms_trajectories, symptoms_tags=symptoms_tags
        )
        return sum(avg_rate_for_symptoms * times_to_symptoms) / sum(
            avg_rate_for_symptoms
        )

    def get_regional_latent_cases(
        self,
    ) -> pd.DataFrame:
        """
        Find regional latent cases from the observed one.

        Returns
        -------
        data frame with latent cases per region indexed by date
        """
        symptoms_tags = ("dead_hospital", "dead_icu")
        symtpoms_rates = self.get_symptoms_rates_per_age_sex()
        avg_hospital_death_rate = self.weight_rates_by_age_sex_per_region(
            symtpoms_rates, symptoms_tags=symptoms_tags
        )
        avg_death_rate_over_regions = np.mean(
            list(avg_hospital_death_rate.values()), axis=0
        )
        hospital_death_trajectories = self.filter_symptoms_trajectories(
            self.symptoms_trajectories, symptoms_to_keep=symptoms_tags
        )

        median_time_to_death = round(
            self.get_weighted_time_to_symptoms(
                hospital_death_trajectories,
                avg_death_rate_over_regions,
                symptoms_tags=symptoms_tags,
            )
        )
        return self.get_latent_cases_per_region(
            self.n_observed_deaths, median_time_to_death, avg_hospital_death_rate
        )
