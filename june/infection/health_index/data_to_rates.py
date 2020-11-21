import logging
import pandas as pd
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
            "We will presume ages from 0 to {lower_age} all have the same value."
        )
        age_intervals[0] = pd.Interval(
            left=0, right=age_intervals[0].right, closed="both"
        )
    if upper_age < 100:
        logger.warning(
            f"Your age intervals do not contain values larger than {upper_age}."
            "We will presume ages {upper_age} all have the same value."
        )
        age_intervals[-1] = pd.Interval(
            left=age_intervals[-1].left, right=100, closed="both"
        )
    df.index = age_intervals
    return df


class Data2Rates:
    def __init__(
        self,
        seroprevalence_df: pd.DataFrame,
        population_by_age_sex_df: pd.DataFrame,
        all_deaths_by_age_sex_df: pd.DataFrame,
        care_home_deaths_by_age_sex_df: pd.DataFrame = None,
    ):
        self.seroprevalence_df = seroprevalence_df
        self.population_by_age_sex_df = population_by_age_sex_df
        self.all_deaths_by_age_sex = all_deaths_by_age_sex_df
        self.care_home_deaths_by_age_sex_df = care_home_deaths_by_age_sex_df

    @classmethod
    def from_files(
        cls,
        seroprevalence_file: str = default_seroprevalence_file,
        population_file: str = default_population_file,
        all_deaths_file: str = default_all_deaths_file,
        care_home_deaths_file: str = default_care_home_deaths_file,
    ) -> "Data2Rates":

        seroprevalence_df = cls.read_csv(seroprevalence_file)
        population_df = cls.read_csv(population_file, converters=False)
        all_deaths_df = cls.read_csv(all_deaths_file, converters=True)
        if care_home_deaths_file is None:
            care_home_deaths_df = None
        else:
            care_home_deaths_df = cls.read_csv(care_home_deaths_file, converters=True)
        return cls(
            seroprevalence_df=seroprevalence_df,
            population_by_age_sex_df=population_df,
            all_deaths_by_age_sex_df=all_deaths_df,
        )

    @classmethod
    def read_csv(cls, filename, converters=True):
        df = pd.read_csv(filename)
        df.set_index("age", inplace=True)
        if converters:
            new_index = convert_to_intervals(df.index)
            df.index = new_index
            df = check_age_intervals(df=df)
        return df

    def get_n_cases(self, age: int, sex: str, is_care_home: bool = False) -> float:
        if is_care_home:
            pass
        else:
            sero_prevalence = self.seroprevalence_df.loc[age, "seroprevalence_weighted"]

            n_people = self.population_by_age_sex_df.loc[age, sex]
            # TODO: remove care home residents
            return n_people * sero_prevalence

    def get_n_deaths(self, age: int, sex: str, is_care_home: bool = False) -> int:
        if is_care_home:
            return self.care_home_deaths_by_age_sex_df.loc[age, sex]
        else:
            deaths_total = self.all_deaths_by_age_sex_df.loc[age, sex]
            if self.care_home_deaths_by_age_sex_df is None:
                return deaths_total
            else:
                return (
                    deaths_total - self.care_home_deaths_by_age_sex_df.loc[age, sex]
                )
    def get_death_rate(self, age_bin: int, sex:str, is_care_home: bool = False) -> float:
        n_cases = self.get_n_cases(age_bin=age_bin, sex=sex, is_care_home=is_care_home)
        n_deaths = self.get_n_deaths(age_bin=age_bin, sex=sex, is_care_home=is_care_home)
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
    plt.legend()
    plt.ylabel("Death rate")
    plt.xlabel("Age")
    plt.show()
