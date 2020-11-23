import logging
import pandas as pd
import numpy as np
from typing import List
from june import paths

hi_data = paths.data_path / "input/health_index"
default_seroprevalence_file = hi_data / "seroprevalence_by_age_imperial.csv"
default_care_home_seroprevalence_file = hi_data / "care_home_seroprevalence_by_age.csv"
default_population_file = hi_data / "corrected_population_by_age_sex_2020_england.csv"
default_all_deaths_file = hi_data / "deaths_by_age_sex_17_july.csv"
default_care_home_deaths_file = hi_data / "care_home_deaths_by_age_sex_17_july.csv"
default_care_home_ratios_by_age_sex_file = (
    hi_data / "care_home_ratios_by_age_sex_england.csv"
)
default_hospital_death_rate_file = hi_data / "cocin_hospital_death_rate.csv"
default_hospital_admissions_by_age_sex_file = (
    hi_data / "cocin_sitrep_hospital_admissions_by_age_sex_17july.csv"
)
default_hospital_deaths_by_age_sex_file = (
    hi_data / "cocin_ons_hospital_deaths_by_age_sex_17july.csv"
)
ifr_imperial_file = paths.data_path / "plotting/health_index/ifr_imperial.csv"
ifr_ward_file = paths.data_path / "plotting/health_index/ifr_ward.csv"

logger = logging.getLogger("rates")

total_sitrep_admissions = 104339


def convert_to_intervals(ages: List[str], is_interval=False) -> pd.IntervalIndex:
    idx = []
    for age in ages:
        if is_interval:
            age = age.strip("[]").split(",")
            idx.append(pd.Interval(left=int(age[0]), right=int(age[1]), closed="both"))
        else:
            idx.append(
                pd.Interval(
                    left=int(age.split("-")[0]),
                    right=int(age.split("-")[1]),
                    closed="both",
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
    if upper_age < 99:
        logger.warning(
            f"Your age intervals do not contain values larger than {upper_age}."
            f"We will presume ages {upper_age} all have the same value."
        )
        age_intervals[-1] = pd.Interval(
            left=age_intervals[-1].left, right=99, closed="both"
        )
    elif upper_age > 99:
        logger.warning(
            f"Your age intervals contain values larger than 99."
            f"Setting that to the be the uper limit"
        )
        age_intervals[-1] = pd.Interval(
            left=age_intervals[-1].left, right=99, closed="both"
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
        hospital_death_rate_by_age_sex_df: pd.DataFrame,
        hospital_deaths_by_age_sex_df: pd.DataFrame,
        hospital_admissions_by_age_sex_df: pd.DataFrame,
        # hospital_admissions_by_age_df: pd.DataFrame,
        care_home_deaths_by_age_sex_df: pd.DataFrame = None,
        care_home_ratios_by_age_sex_df: pd.DataFrame = None,
        care_home_seroprevalence_by_age_df: pd.DataFrame = None,
        care_home_deaths_at_hospital_ratio=0.2,
    ):
        # seroprev
        self.seroprevalence_df = self._process_df(seroprevalence_df, converters=True)
        self.care_home_seroprevalence_by_age_df = self._process_df(
            care_home_seroprevalence_by_age_df, converters=True
        )

        # populations
        self.population_by_age_sex_df = self._process_df(
            population_by_age_sex_df, converters=False
        )
        self.care_home_ratios_by_age_sex_df = self._process_df(
            care_home_ratios_by_age_sex_df, converters=False
        )
        self.care_home_ratios_by_age_sex_df.loc[:50, "male"] = 0
        self.care_home_ratios_by_age_sex_df.loc[:50, "female"] = 0
        self.all_deaths_by_age_sex_df = self._process_df(
            all_deaths_by_age_sex_df, converters=True
        )
        self.care_home_deaths_by_age_sex_df = self._process_df(
            care_home_deaths_by_age_sex_df, converters=True
        )
        self.hospital_deaths_by_age_sex_df = self._process_df(
            hospital_deaths_by_age_sex_df, converters=True
        )
        self.hospital_admissions_by_age_sex_df = self._process_df(
            hospital_admissions_by_age_sex_df, converters=True
        )
        self.hospital_death_rate_by_age_sex_df = self._process_df(
            hospital_death_rate_by_age_sex_df, converters=True
        )
        self.care_home_deaths_at_hospital_ratio = care_home_deaths_at_hospital_ratio
        self.gp_mapper = (
            lambda age, sex:  1#self.population_by_age_sex_df.loc[age, sex]
        )
        self.ch_mapper = lambda age, sex: self.care_home_ratios_by_age_sex_df.loc[
            age, sex
        ] * self.gp_mapper(age, sex)

    @classmethod
    def from_file(
        cls,
        seroprevalence_file: str = default_seroprevalence_file,
        population_file: str = default_population_file,
        all_deaths_file: str = default_all_deaths_file,
        hospital_death_rate_file: str = default_hospital_death_rate_file,
        hospital_deaths_file: str = default_hospital_deaths_by_age_sex_file,
        hospital_admissions_file: str = default_hospital_admissions_by_age_sex_file,
        care_home_deaths_file: str = default_care_home_deaths_file,
        care_home_ratios_by_age_sex_file: str = default_care_home_ratios_by_age_sex_file,
        care_home_seroprevalence_by_age_file: str = default_care_home_seroprevalence_file,
    ) -> "Data2Rates":

        seroprevalence_df = cls._read_csv(seroprevalence_file)
        population_df = cls._read_csv(population_file)
        all_deaths_df = cls._read_csv(all_deaths_file)
        hospital_deaths_df = cls._read_csv(hospital_deaths_file)
        hospital_admissions_df = cls._read_csv(hospital_admissions_file)
        hospital_death_rate_df = cls._read_csv(hospital_death_rate_file)
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
        if care_home_seroprevalence_by_age_file is None:
            care_home_seroprevalence_by_age_df = None
        else:
            care_home_seroprevalence_by_age_df = cls._read_csv(
                care_home_seroprevalence_by_age_file
            )
        return cls(
            seroprevalence_df=seroprevalence_df,
            population_by_age_sex_df=population_df,
            all_deaths_by_age_sex_df=all_deaths_df,
            hospital_deaths_by_age_sex_df=hospital_deaths_df,
            hospital_admissions_by_age_sex_df=hospital_admissions_df,
            hospital_death_rate_by_age_sex_df=hospital_death_rate_df,
            care_home_deaths_by_age_sex_df=care_home_deaths_df,
            care_home_ratios_by_age_sex_df=care_home_ratios_by_age_sex_df,
            care_home_seroprevalence_by_age_df=care_home_seroprevalence_by_age_df,
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

    def _get_interpolated_value(self, df, age, sex, weight_mapper=None):
        """
        Interpolates bins to single years by weighting each year by its population times
        the death rate

        Parameters
        ----------
        df
            dataframe with the structure
            age | male | female
            0-5 | 2    | 3
            etc.
       weight_mapper 
            function mapping (age,sex) -> weight
            if not provided uses population weight.
        """
        if weight_mapper is None:
            weight_mapper = lambda age, sex: 1
        age_bin = df.loc[age].name
        data_bin = df.loc[age, sex]
        bin_weight = sum(
            [
                weight_mapper(age_i, sex)
                for age_i in range(age_bin.left, age_bin.right + 1)
            ]
        )
        if bin_weight == 0:
            return 0
        value_weight = weight_mapper(age, sex)
        return value_weight * data_bin / bin_weight

    def get_n_cases(self, age: int, sex: str, is_care_home: bool = False) -> float:
        if is_care_home:
            sero_prevalence = self.care_home_seroprevalence_by_age_df.loc[
                age, "seroprevalence"
            ]
            n_people = self.population_by_age_sex_df.loc[age, sex]
            n_people *= self.care_home_ratios_by_age_sex_df.loc[age, sex]

        else:
            sero_prevalence = self.seroprevalence_df.loc[age, "seroprevalence"]
            n_people = self.population_by_age_sex_df.loc[age, sex]
            if self.care_home_ratios_by_age_sex_df is not None:
                n_people -= n_people * self.care_home_ratios_by_age_sex_df.loc[age, sex]
        n_cases = n_people * sero_prevalence
        # correct for deaths
        n_cases += self.get_n_deaths(age=age, sex=sex, is_care_home=is_care_home)
        return n_cases

    def get_care_home_deaths(self, age: int, sex: str):
        return self._get_interpolated_value(
            df=self.care_home_deaths_by_age_sex_df,
            age=age,
            sex=sex,
            weight_mapper=self.ch_mapper,
        )

    def get_all_deaths(self, age: int, sex: str):
        return self._get_interpolated_value(
            df=self.all_deaths_by_age_sex_df,
            age=age,
            sex=sex,
            weight_mapper=self.gp_mapper,
        )

    def get_n_deaths(self, age: int, sex: str, is_care_home: bool = False) -> int:
        if is_care_home:
            return self.get_care_home_deaths(age=age, sex=sex)
        else:
            deaths_total = self.get_all_deaths(age=age, sex=sex)
            if self.care_home_deaths_by_age_sex_df is None:
                return deaths_total
            else:
                deaths_care_home = self.get_care_home_deaths(age=age, sex=sex)
                return deaths_total - deaths_care_home

    def get_infection_fatality_rate(
        self, age: int, sex: str, is_care_home: bool = False
    ) -> float:
        n_cases = self.get_n_cases(age=age, sex=sex, is_care_home=is_care_home)
        n_deaths = self.get_n_deaths(age=age, sex=sex, is_care_home=is_care_home)
        if n_cases * n_deaths == 0:
            return 0
        else:
            return n_deaths / n_cases

    #### hospital ####
    def get_all_hospital_deaths(self, age: int, sex: str):
        return self._get_interpolated_value(
            df=self.hospital_deaths_by_age_sex_df,
            age=age,
            sex=sex,
            weight_mapper=self.gp_mapper,
        )

    def get_care_home_hospital_deaths(self, age: int, sex: str):
        return (
            self._get_interpolated_value(
                df=self.hospital_deaths_by_age_sex_df,
                age=age,
                sex=sex,
                weight_mapper=self.ch_mapper,
            )
            * self.care_home_deaths_at_hospital_ratio
        )

    def get_n_hospital_deaths(
        self, age: int, sex: str, is_care_home: bool = False
    ) -> int:
        care_home_deaths = self.get_care_home_hospital_deaths(age=age, sex=sex)
        if is_care_home:
            return care_home_deaths
        else:
            all_deaths = self.get_all_hospital_deaths(age=age, sex=sex)
            return all_deaths - care_home_deaths

    def get_all_hospital_admissions(self, age: int, sex: str):
        return self._get_interpolated_value(
            df=self.hospital_admissions_by_age_sex_df,
            age=age,
            sex=sex,
            weight_mapper=self.gp_mapper,
        )

    def get_care_home_hospital_admissions(self, age: int, sex: str):
        return (
            self._get_interpolated_value(
                df=self.hospital_admissions_by_age_sex_df,
                age=age,
                sex=sex,
                weight_mapper=self.ch_mapper,
            )
            * self.care_home_deaths_at_hospital_ratio
        )

    def get_n_hospital_admissions(
        self, age: int, sex: str, is_care_home: bool = False
    ) -> int:
        care_home_admissions = self.get_care_home_hospital_admissions(age=age, sex=sex)
        if is_care_home:
            return care_home_admissions
        else:
            all_admissions = self.get_all_hospital_admissions(age=age, sex=sex)
            return all_admissions - care_home_admissions

    def get_hospital_death_rate(
        self, age: int, sex: str, is_care_home: bool = False
    ) -> int:
        return self.get_n_hospital_deaths(
            age=age, sex=sex, is_care_home=is_care_home
        ) / self.get_n_hospital_admissions(age=age, sex=sex, is_care_home=is_care_home)

    def get_hospital_infection_fatality_rate(
        self, age: int, sex: str, is_care_home: bool = False
    ) -> int:
        n_cases = self.get_n_cases(age=age, sex=sex, is_care_home=is_care_home)
        n_hospital_deaths = self.get_n_hospital_deaths(
            age=age, sex=sex, is_care_home=is_care_home
        )
        if n_cases * n_hospital_deaths == 0:
            return 0
        return n_hospital_deaths / n_cases

    def get_hospital_infection_admission_rate(
        self, age: int, sex: str, is_care_home: bool = False
    ) -> int:
        n_cases = self.get_n_cases(age=age, sex=sex, is_care_home=is_care_home)
        n_hospital_admissions = self.get_n_hospital_admissions(
            age=age, sex=sex, is_care_home=is_care_home
        )
        return n_hospital_admissions / n_cases

    #### home ####
    def get_all_home_deaths(self, age: int, sex: str):
        return self.get_all_deaths(age=age, sex=sex) - self.get_all_hospital_deaths(
            age=age, sex=sex
        )

    def get_care_home_home_deaths(self, age: int, sex: str):
        return self.get_care_home_home_deaths(
            age=age, sex=sex
        ) - self.get_care_home_hospital_deaths(age=age, sex=sex)

    def get_n_home_deaths(self, age: int, sex: str, is_care_home: bool = False):
        return self.get_n_deaths(
            age=age, sex=sex, is_care_home=is_care_home
        ) - self.get_n_hospital_deaths(age=age, sex=sex, is_care_home=is_care_home)

    def get_home_infection_fatality_rate(
        self, age: int, sex: str, is_care_home: bool = False
    ):
        n_cases = self.get_n_cases(age=age, sex=sex, is_care_home=is_care_home)
        n_home_deaths = self.get_n_home_deaths(
            age=age, sex=sex, is_care_home=is_care_home
        )
        if n_cases * n_home_deaths == 0:
            return 0
        return n_home_deaths / n_cases

    ##### utils #####
    def get_value_at_bin(
        self,
        f,
        age_bin: pd.Interval,
        sex: str,
        is_care_home: bool = False,
        weight_mapper=None,
    ):
        age_range = range(age_bin.left, age_bin.right + 1)
        if sex == "all":
            male_values = []
            female_values = []
            male_bin_weight = sum(weight_mapper(age, "male") for age in age_range)
            female_bin_weight = sum(weight_mapper(age, "female") for age in age_range)
            for age in age_range:
                male_value = f(age=age, sex="male", is_care_home=is_care_home)
                female_value = f(age=age, sex="female", is_care_home=is_care_home)
                male_values.append(male_value * weight_mapper(age, "male"))
                female_values.append(female_value * weight_mapper(age, "female"))
            if male_bin_weight == 0:
                male_avg = 0
            else:
                male_avg = sum(male_values) / male_bin_weight
            if female_bin_weight:
                female_avg = 0
            else:
                female_avg = sum(female_values) / female_bin_weight
            if male_avg + female_avg == 0:
                return 0
            return (male_bin_weight * male_avg + female_bin_weight * female_avg) / (
                male_bin_weight + female_bin_weight
            )
        else:
            values = []
            bin_total_weight = sum(weight_mapper(age, sex) for age in age_range)
            if bin_total_weight == 0:
                return 0
            for age in age_range:
                value = f(age=age, sex=sex, is_care_home=is_care_home)
                values.append(value * weight_mapper(age, sex))
            return sum(values) / bin_total_weight


def get_outputs_df(rates, age_bins):
    outputs = pd.DataFrame(index=age_bins,)
    gp_mapper = rates.gp_mapper
    ch_mapper = rates.ch_mapper
    for pop in ["gp", "ch"]:
        if pop == "ch":
            mapper = ch_mapper
            ch = True
        else:
            mapper = gp_mapper
            ch = False
        for sex in ["male", "female", "all"]:
            for fname, function in zip(
                ["ifr", "hospital_ifr", "admissions", "home_ifr"],
                [
                    rates.get_infection_fatality_rate,
                    rates.get_hospital_infection_fatality_rate,
                    rates.get_hospital_infection_admission_rate,
                    rates.get_home_infection_fatality_rate,
                ],
            ):
                colname = f"{pop}_{fname}_{sex}"
                for age_bin in age_bins:
                    outputs.loc[age_bin, colname] = (
                        rates.get_value_at_bin(
                            f=function,
                            age_bin=age_bin,
                            sex=sex,
                            is_care_home=ch,
                            weight_mapper=mapper,
                        )
                        * 100
                    )
    return outputs


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    rates = Data2Rates.from_file()
    ### OVERALL IFR ###
    ##### June results vs Imperial #####
    ifr_imperial = pd.read_csv(ifr_imperial_file, index_col=0)
    ifr_imperial.index = convert_to_intervals(ifr_imperial.index, is_interval=True)
    fig, ax = plt.subplots()
    outputs = get_outputs_df(rates=rates, age_bins=ifr_imperial.index)
    outputs.to_csv("hi_outputs.csv")
    # june_ifrs.loc[:, ["ch_male", "ch_female", "ch_all"]].plot.bar(
    #    ax=ax, color=["C0", "C1", "C2"], alpha=0.5, width=0.8, label="June",
    # )
    # plt.show()
    # errors = np.array([ifr_imperial.error_low, ifr_imperial.error_high]).reshape(2, -1)
    # ifr_imperial.plot.bar(
    #    y="ifr",
    #    ax=ax,
    #    label="Imperial",
    #    color="C3",
    #    alpha=0.7,
    #    legend=False,
    #    yerr=errors,
    #    capsize=4,
    # )
    # ax.legend()
    # plt.ylabel("IFR")
    # plt.savefig("ifr_imperial_vs_june.png", dpi=150, bbox_inches="tight")
    # plt.show()

    ## June comparison vs Ward ##
    # ifr_ward = pd.read_csv(ifr_ward_file, index_col=0)
    # ifr_ward.index = convert_to_intervals(ifr_ward.index, is_interval=True)
    # fig, ax = plt.subplots()
    # june_ifrs.loc[:, ["gp_male", "gp_female", "gp_all"]].plot.bar(
    #    ax=ax,
    #    color=["C0", "C1", "C2"],
    #    alpha=0.5,
    #    width=0.8,
    #    label="June",
    #    legend=False,
    # )
    # errors = np.array([ifr_ward.error_low, ifr_ward.error_high]).reshape(2, -1)
    # ifr_ward.plot.bar(
    #    ax=ax,
    #    y="ifr",
    #    label="Ward",
    #    color="C3",
    #    alpha=0.7,
    #    legend=False,
    #    yerr=errors,
    #    capsize=4,
    # )
    # ax.legend()
    # plt.ylabel("IFR")
    # plt.savefig("ifr_ward_vs_june.png", dpi=150, bbox_inches="tight")
    # plt.show()

    # age_bins = [
    #    pd.Interval(left=i, right=i + 4, closed="both") for i in range(0, 90, 5)
    # ]
    # age_bins.append(pd.Interval(left=90, right=99, closed="both"))
    ## deaths vs hospital deaths
    # fig, ax = plt.subplots()
    # deaths_df = pd.DataFrame(index=age_bins)
    # deaths_df["gp_male"] = [
    #    rates.get_value_at_bin(
    #        age_bin=age_bin,
    #        sex="male",
    #        f=rates.get_n_deaths,
    #        weight_mapper=rates.gp_mapper,
    #        is_care_home=False,
    #    )
    #    for age_bin in age_bins
    # ]
    # deaths_df["gp_hospital_male"] = [
    #    rates.get_value_at_bin(
    #        age_bin=age_bin,
    #        f=rates.get_n_hospital_deaths,
    #        sex="male",
    #        weight_mapper=rates.gp_mapper,
    #        is_care_home=False,
    #    )
    #    for age_bin in age_bins
    # ]
    # deaths_df["gp_hospital_male"] *= 1.65  # ons / cocin ratio
    # deaths_df.plot.bar(ax=ax)
    # plt.show()

    ## Hospital vs non-hospital IFRS
    # june_ifrs = get_IFR_dataframe(rates=rates, age_bins=age_bins)
    # toplot = june_ifrs.loc[
    #    :, ["gp_male", "gp_female", "gp_hospital_male", "gp_hospital_female"]
    # ]
    # fig, ax = plt.subplots()
    # toplot.plot.bar(ax=ax)
    # plt.show()
    # asd = rates.population_by_age_sex_df * rates.care_home_ratios_by_age_sex_df
