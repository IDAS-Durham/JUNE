import logging
import pandas as pd
import numpy as np
from typing import List
from june import paths

default_seroprevalence_file = (
    paths.data_path / "input/health_index/seroprevalence_by_age_imperial.csv"
)
default_population_file = (
    paths.data_path
    / "input/health_index/corrected_population_by_age_sex_2020_england.csv"
)
default_all_deaths_file = (
    paths.data_path / "input/health_index/deaths_by_age_sex_17_july.csv"
)
default_care_home_deaths_file = (
    paths.data_path / "input/health_index/care_home_deaths_by_age_sex_17_july.csv"
)
default_care_home_ratios_by_age_sex_file = (
    paths.data_path / "input/health_index/care_home_ratios_by_age_sex_england.csv"
)

logger = logging.getLogger("rates")


def convert_to_intervals(ages: List[str]) -> pd.IntervalIndex:
    idx = []
    for age in ages:
        idx.append(
            pd.Interval(
                left=int(age.split("-")[0]), right=int(age.split("-")[1]), closed="both"
            )
        )
    return pd.IntervalIndex(idx)


def check_age_intervals(df: pd.DataFrame):
    age_intervals = list(df.index)
    lower_age = age_intervals[0].left
    upper_age = age_intervals[-1].right
    if lower_age != 0:
        logger.warning(
            f"Your age intervals do not contain values smaller than {lower_age}."
            f"We will presume ages from 0 to {lower_age} all have the same value."
        )
        age_intervals[0] = pd.Interval(
            left=0, right=age_intervals[0].right, closed="both"
        )
    if upper_age < 100:
        logger.warning(
            f"Your age intervals do not contain values larger than {upper_age}."
            f"We will presume ages {upper_age} all have the same value."
        )
        age_intervals[-1] = pd.Interval(
            left=age_intervals[-1].left, right=100, closed="both"
        )
    df.index = age_intervals
    return df


def weighted_interpolation(value, weights):
    weights = np.array(weights)
    return weights * value / weights.sum()


class Data2Rates:
    def __init__(
        self,
        seroprevalence_df: pd.DataFrame,
        population_by_age_sex_df: pd.DataFrame,
        all_deaths_by_age_sex_df: pd.DataFrame,
        care_home_deaths_by_age_sex_df: pd.DataFrame = None,
        care_home_ratios_by_age_sex_df: pd.DataFrame = None,
    ):
        self.seroprevalence_df = self._process_df(seroprevalence_df, converters=True)
        self.population_by_age_sex_df = self._process_df(
            population_by_age_sex_df, converters=False
        )
        self.all_deaths_by_age_sex_df = self._process_df(
            all_deaths_by_age_sex_df, converters=True, interpolate_bins=True
        )
        self.care_home_deaths_by_age_sex_df = self._process_df(
            care_home_deaths_by_age_sex_df, converters=True, interpolate_bins=True
        )
        self.care_home_ratios_by_age_sex_df = self._process_df(
            care_home_ratios_by_age_sex_df, converters=False
        )

    @classmethod
    def from_files(
        cls,
        seroprevalence_file: str = default_seroprevalence_file,
        population_file: str = default_population_file,
        all_deaths_file: str = default_all_deaths_file,
        care_home_deaths_file: str = default_care_home_deaths_file,
        care_home_ratios_by_age_sex_file: str = default_care_home_ratios_by_age_sex_file,
    ) -> "Data2Rates":

        seroprevalence_df = cls._read_csv(seroprevalence_file)
        population_df = cls._read_csv(population_file)
        all_deaths_df = cls._read_csv(all_deaths_file)
        if care_home_deaths_file is None:
            care_home_deaths_df = None
        else:
            care_home_deaths_df = cls._read_csv(care_home_deaths_file)
        if care_home_ratios_by_age_sex_file is None:
            care_home_ratios_by_age_sex_df = None
        else:
            care_home_ratios_by_age_sex_df = cls._read_csv(
                care_home_ratios_by_age_sex_file
            )
        return cls(
            seroprevalence_df=seroprevalence_df,
            population_by_age_sex_df=population_df,
            all_deaths_by_age_sex_df=all_deaths_df,
            care_home_deaths_by_age_sex_df=care_home_deaths_df,
            care_home_ratios_by_age_sex_df=care_home_ratios_by_age_sex_df,
        )

    @classmethod
    def _read_csv(cls, filename):
        df = pd.read_csv(filename)
        df.set_index("age", inplace=True)
        return df

    def _process_df(self, df, converters=True, interpolate_bins=False):
        if converters:
            new_index = convert_to_intervals(df.index)
            df.index = new_index
            df = check_age_intervals(df=df)
        if interpolate_bins:
            df = self._interpolate_bins(df=df)
        return df

    def _interpolate_bins(self, df):
        ret = pd.DataFrame(index=np.arange(df.index[0].left, 100), columns=df.columns)
        for age_bin, row in df.iterrows():
            age_min = age_bin.left
            age_max = min(age_bin.right, 99)
            males = self.population_by_age_sex_df.loc[age_min:age_max, "male"].values
            females = self.population_by_age_sex_df.loc[
                age_min:age_max, "female"
            ].values
            male_values = weighted_interpolation(value=row["male"], weights=males)
            female_values = weighted_interpolation(value=row["female"], weights=females)
            ret.loc[age_min:age_max, "male"] = male_values
            ret.loc[age_min:age_max, "female"] = female_values
        return ret

    def get_n_cases(self, age: int, sex: str, is_care_home: bool = False) -> float:
        if is_care_home:
            pass
        else:
            sero_prevalence = self.seroprevalence_df.loc[age, "seroprevalence_weighted"]
            n_people = self.population_by_age_sex_df.loc[age, sex]
            if self.care_home_ratios_by_age_sex_df is not None:
                n_people -= n_people * self.care_home_ratios_by_age_sex_df.loc[age, sex]
            return n_people * sero_prevalence

    def get_n_deaths(self, age: int, sex: str, is_care_home: bool = False) -> int:
        if is_care_home:
            return self.care_home_deaths_by_age_sex_df.loc[age, sex]
        else:
            deaths_total = self.all_deaths_by_age_sex_df.loc[age, sex]
            if self.care_home_deaths_by_age_sex_df is None:
                return deaths_total
            else:
                return deaths_total - self.care_home_deaths_by_age_sex_df.loc[age, sex]

    def get_death_rate(self, age: int, sex: str, is_care_home: bool = False) -> float:
        n_cases = self.get_n_cases(age=age, sex=sex, is_care_home=is_care_home)
        n_deaths = self.get_n_deaths(age=age, sex=sex, is_care_home=is_care_home)
        return n_deaths / n_cases


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    rates = Data2Rates.from_files()
    # ***************** Ward et al IFR
    ifr_age = [0.03, 0.52, 3.13, 11.64]
    ages = [
        pd.Interval(15, 44, closed="left"),
        pd.Interval(45, 64, closed="left"),
        pd.Interval(65, 74, closed="left"),
        pd.Interval(75, 100, closed="left"),
    ]
    index = pd.IntervalIndex(ages)
    ifr_ward = pd.DataFrame(ifr_age, index=index)
    # ***************** Imperial IFR
    ifr_age = [
        0.0,
        0.01,
        0.01,
        0.02,
        0.03,
        0.04,
        0.06,
        0.1,
        0.16,
        0.24,
        0.38,
        0.6,
        0.94,
        1.47,
        2.31,
        3.61,
        5.66,
        8.86,
        17.37,
    ]
    ages = [pd.Interval(i, i + 5, closed="left") for i in range(0, 90, 5)]
    ages += [pd.Interval(90, 100, closed="left")]
    index = pd.IntervalIndex(ages)
    ifr_imperial = pd.DataFrame(ifr_age, index=index)
    ages = np.arange(0, 100)
    male_drs = []
    female_drs = []
    all_drs = []
    for age in ages:
        male_dr = rates.get_death_rate(age=age, sex="male")
        female_dr = rates.get_death_rate(age=age, sex="female")
        male_drs.append(male_dr)
        female_drs.append(female_dr)
        male_pop = rates.population_by_age_sex_df.loc[age, "male"]
        female_pop = rates.population_by_age_sex_df.loc[age, "female"]
        all_drs.append((male_pop * male_dr + female_pop * female_dr)/ (male_pop + female_pop))
    # ******************* IFR comparison
    plt.bar(
        x=[index.mid for index in ifr_ward.index],
        height=ifr_ward[0].values,
        width=[index.right - index.left for index in ifr_ward.index],
        alpha=0.4,
        label="Ward",
    )
    plt.bar(
        x=[index.mid for index in ifr_imperial.index],
        height=ifr_imperial[0].values,
        width=[index.right - index.left for index in ifr_imperial.index],
        alpha=0.4,
        label="Imperial",
    )
    plt.plot(ages, 100 * np.array(male_drs), label="male death rate")
    plt.plot(ages, 100 * np.array(female_drs), label="female death rate")
    plt.plot(ages, 100 * np.array(all_drs), label="average death rate")
    plt.legend()
    plt.ylabel("Death rate")
    plt.xlabel("Age")
    plt.show()
