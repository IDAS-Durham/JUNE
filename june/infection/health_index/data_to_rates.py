import logging
import pandas as pd
import numpy as np
from typing import List, Union, Optional
from june import paths

# TODO: Add: get_severe_proportion + get_icu_ifr + get_icu_admissions_rate

# ch = care home, gp = general population (so everyone not in a care home)

hi_data = paths.data_path / "input/health_index"
default_seroprevalence_file = hi_data / "seroprevalence_by_age.csv"
default_care_home_seroprevalence_file = hi_data / "care_home_seroprevalence_by_age.csv"

default_population_file = hi_data / "population_by_age_sex_2020_england.csv"
default_care_home_population_file = hi_data / "care_home_residents_by_age_sex_june.csv"

default_all_deaths_file = hi_data / "all_deaths_by_age_sex.csv"
default_care_home_deaths_file = hi_data / "care_home_deaths_by_age_sex.csv"
default_gp_admissions_file = hi_data / "cocin_gp_hospital_admissions_by_age_sex.csv"
default_ch_admissions_file = hi_data / "chess_ch_hospital_admissions_by_age_sex.csv"
default_gp_hospital_deaths_file = hi_data / "cocin_gp_hospital_deaths_by_age_sex.csv"
default_ch_hospital_deaths_file = hi_data / "chess_ch_hospital_deaths_by_age_sex.csv"
ifr_imperial_file = paths.data_path / "plotting/health_index/ifr_imperial.csv"
ifr_ward_file = paths.data_path / "plotting/health_index/ifr_ward.csv"

logger = logging.getLogger("rates")


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


def read_comorbidity_csv(filename: str):
    comorbidity_df = pd.read_csv(filename, index_col=0)
    column_names = [f"0-{comorbidity_df.columns[0]}"]
    for i in range(len(comorbidity_df.columns) - 1):
        column_names.append(
            f"{comorbidity_df.columns[i]}-{comorbidity_df.columns[i+1]}"
        )
    comorbidity_df.columns = column_names
    for column in comorbidity_df.columns:
        no_comorbidity = comorbidity_df[column].loc["no_condition"]
        should_have_comorbidity = 1 - no_comorbidity
        has_comorbidity = np.sum(comorbidity_df[column]) - no_comorbidity
        comorbidity_df[column].iloc[:-1] *= should_have_comorbidity / has_comorbidity

    return comorbidity_df.T


def convert_comorbidities_prevalence_to_dict(prevalence_female, prevalence_male):
    prevalence_reference_population = {}
    for comorbidity in prevalence_female.columns:
        prevalence_reference_population[comorbidity] = {
            "f": prevalence_female[comorbidity].to_dict(),
            "m": prevalence_male[comorbidity].to_dict(),
        }
    return prevalence_reference_population


class Data2Rates:
    def __init__(
        self,
        seroprevalence_df: pd.DataFrame,
        population_by_age_sex_df: pd.DataFrame,
        care_home_population_by_age_sex_df: pd.DataFrame,
        all_deaths_by_age_sex_df: pd.DataFrame,
        hospital_gp_deaths_by_age_sex_df: pd.DataFrame,
        hospital_ch_deaths_by_age_sex_df: pd.DataFrame,
        hospital_gp_admissions_by_age_sex_df: pd.DataFrame,
        hospital_ch_admissions_by_age_sex_df: pd.DataFrame,
        care_home_deaths_by_age_sex_df: pd.DataFrame = None,
        care_home_seroprevalence_by_age_df: pd.DataFrame = None,
        probability_dying_at_home=0.05,
        probability_dying_at_home_care_home=0.7,
        comorbidity_multipliers: Optional[dict] = None,
        comorbidity_prevalence_reference_population: Optional[dict] = None,
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
        self.gp_mapper = (
            lambda age, sex: self.population_by_age_sex_df.loc[age, sex]
            - self.care_home_population_by_age_sex_df.loc[age, sex]
        )
        self.care_home_population_by_age_sex_df = self._process_df(
            care_home_population_by_age_sex_df, converters=False
        )
        self.ch_mapper = lambda age, sex: self.care_home_population_by_age_sex_df.loc[
            age, sex
        ]
        self.all_deaths_by_age_sex_df = self._process_df(
            all_deaths_by_age_sex_df, converters=True
        )
        self.care_home_deaths_by_age_sex_df = self._process_df(
            care_home_deaths_by_age_sex_df, converters=True
        )
        self.hospital_gp_deaths_by_age_sex_df = self._process_df(
            hospital_gp_deaths_by_age_sex_df, converters=True
        )
        self.hospital_ch_deaths_by_age_sex_df = self._process_df(
            hospital_ch_deaths_by_age_sex_df, converters=True
        )
        self.hospital_gp_admissions_by_age_sex_df = self._process_df(
            hospital_gp_admissions_by_age_sex_df, converters=True
        )
        self.hospital_ch_admissions_by_age_sex_df = self._process_df(
            hospital_ch_admissions_by_age_sex_df, converters=True
        )
        self.probability_dying_at_home = probability_dying_at_home
        self.probability_dying_at_home_care_home = probability_dying_at_home_care_home
        self.comorbidity_multipliers = comorbidity_multipliers
        self.comorbidity_prevalence_reference_population = (
            comorbidity_prevalence_reference_population
        )

    @classmethod
    def from_file(
        cls,
        seroprevalence_file: str = default_seroprevalence_file,
        care_home_seroprevalence_by_age_file: str = default_care_home_seroprevalence_file,
        population_file: str = default_population_file,
        care_home_population_file: str = default_care_home_population_file,
        all_deaths_file: str = default_all_deaths_file,
        hospital_gp_deaths_file: str = default_gp_hospital_deaths_file,
        hospital_ch_deaths_file: str = default_ch_hospital_deaths_file,
        hospital_gp_admissions_file: str = default_gp_admissions_file,
        hospital_ch_admissions_file: str = default_ch_admissions_file,
        care_home_deaths_file: str = default_care_home_deaths_file,
        comorbidity_multipliers_file: Optional[str] = None,
        comorbidity_prevalence_female_file: Optional[str] = None,
        comorbidity_prevalence_male_file: Optional[str] = None,
        probability_dying_at_home=0.05,
        probability_dying_at_home_care_home=0.7,
    ) -> "Data2Rates":

        seroprevalence_df = cls._read_csv(seroprevalence_file)
        population_df = cls._read_csv(population_file)
        all_deaths_df = cls._read_csv(all_deaths_file)
        hospital_gp_deaths_df = cls._read_csv(hospital_gp_deaths_file)
        hospital_ch_deaths_df = cls._read_csv(hospital_ch_deaths_file)
        hospital_gp_admissions_df = cls._read_csv(hospital_gp_admissions_file)
        hospital_ch_admissions_df = cls._read_csv(hospital_ch_admissions_file)
        if care_home_deaths_file is None:
            care_home_deaths_df = None
        else:
            care_home_deaths_df = cls._read_csv(care_home_deaths_file)
        if care_home_population_file is None:
            care_home_population_df = None
        else:
            care_home_population_df = cls._read_csv(care_home_population_file)
        if care_home_seroprevalence_by_age_file is None:
            care_home_seroprevalence_by_age_df = None
        else:
            care_home_seroprevalence_by_age_df = cls._read_csv(
                care_home_seroprevalence_by_age_file
            )
        if comorbidity_multipliers_file is not None:
            with open(multipliers_path) as f:
                comorbidity_multipliers = yaml.load(f, Loader=yaml.FullLoader)
        else:
            comorbidity_multipliers = None
        if (
            comorbidity_prevalence_female_file is not None
            and comorbidity_prevalence_male_file is not None
        ):
            comorbidity_female_prevalence = read_comorbidity_csv(
                comorbidity_prevalence_female_file
            )
            comorbidity_male_prevalence = read_comorbidity_csv(
                comorbidity_prevalence_male_file
            )
            prevalence_reference_population = convert_comorbidities_prevalence_to_dict(
                comorbidity_female_prevalence, comorbidity_male_prevalence
            )
        else:
            prevalence_reference_population = None
        return cls(
            seroprevalence_df=seroprevalence_df,
            population_by_age_sex_df=population_df,
            care_home_population_by_age_sex_df=care_home_population_df,
            all_deaths_by_age_sex_df=all_deaths_df,
            hospital_gp_deaths_by_age_sex_df=hospital_gp_deaths_df,
            hospital_ch_deaths_by_age_sex_df=hospital_ch_deaths_df,
            hospital_gp_admissions_by_age_sex_df=hospital_gp_admissions_df,
            hospital_ch_admissions_by_age_sex_df=hospital_ch_admissions_df,
            care_home_deaths_by_age_sex_df=care_home_deaths_df,
            care_home_seroprevalence_by_age_df=care_home_seroprevalence_by_age_df,
            probability_dying_at_home_care_home=probability_dying_at_home_care_home,
            probability_dying_at_home=probability_dying_at_home,
            comorbidity_multipliers=comorbidity_multipliers,
            comorbidity_prevalence_reference_population=prevalence_reference_population,
        )

    @classmethod
    def _read_csv(cls, filename):
        df = pd.read_csv(filename)
        df.set_index("age", inplace=True)
        return df

    def _process_df(self, df, converters=True):
        if converters:
            new_index = convert_to_intervals(df.index)
            df.index = new_index
            df = check_age_intervals(df=df)
        df = df.sort_index()
        return df

    def _process_care_home_df(self, df):
        df = self._process_df(df, converters=True)
        ages = range(0, 100)
        ret = pd.DataFrame(index=ages)
        mapper = lambda age, sex: self.population_by_age_sex_df.loc[age, sex]
        ret["male"] = np.array(
            [
                self._get_interpolated_value(
                    df=df, age=age, weight_mapper=mapper, sex="male"
                )
                for age in ages
            ]
        )
        ret["female"] = np.array(
            [
                self._get_interpolated_value(
                    df=df, age=age, weight_mapper=mapper, sex="female"
                )
                for age in ages
            ]
        )
        return ret

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

    def get_n_care_home(self, age: int, sex: str):
        return self.care_home_population_by_age_sex_df.loc[age, sex]

    def get_n_cases(self, age: int, sex: str, is_care_home: bool = False) -> float:
        if is_care_home:
            sero_prevalence = self.care_home_seroprevalence_by_age_df.loc[
                age, "seroprevalence"
            ]
            n_people = self.get_n_care_home(age, sex)
        else:
            sero_prevalence = self.seroprevalence_df.loc[age, "seroprevalence"]
            n_people = self.population_by_age_sex_df.loc[age, sex]
            if self.care_home_population_by_age_sex_df is not None:
                n_people -= self.get_n_care_home(age=age, sex=sex)
        # including death correction
        n_deaths = self.get_n_deaths(age=age, sex=sex, is_care_home=is_care_home)
        n_cases = (n_people - n_deaths) * sero_prevalence + n_deaths
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

    #### hospital ####
    def get_all_hospital_deaths(self, age: int, sex: str):
        return self.get_care_home_hospital_deaths(
            age=age, sex=sex
        ) + self.get_gp_hospital_deaths(age=age, sex=sex)

    def get_gp_hospital_deaths(self, age: int, sex: str):
        return self._get_interpolated_value(
            df=self.hospital_gp_deaths_by_age_sex_df,
            age=age,
            sex=sex,
            weight_mapper=self.gp_mapper,
        )

    def get_care_home_hospital_deaths(self, age: int, sex: str):
        return self._get_interpolated_value(
            df=self.hospital_ch_deaths_by_age_sex_df,
            age=age,
            sex=sex,
            weight_mapper=self.ch_mapper,
        )

    def get_n_hospital_deaths(
        self, age: int, sex: str, is_care_home: bool = False
    ) -> int:
        if is_care_home:
            return self.get_care_home_hospital_deaths(age=age, sex=sex)
        else:
            return self.get_gp_hospital_deaths(age=age, sex=sex)

    def get_all_hospital_admissions(self, age: int, sex: str):
        return self.get_care_home_hospital_admissions(
            age=age, sex=sex
        ) + self.get_gp_hospital_admissions(age=age, sex=sex)

    def get_gp_hospital_admissions(self, age: int, sex: str):
        return self._get_interpolated_value(
            df=self.hospital_gp_admissions_by_age_sex_df,
            age=age,
            sex=sex,
            weight_mapper=self.gp_mapper,
        )

    def get_care_home_hospital_admissions(self, age: int, sex: str):
        return self._get_interpolated_value(
            df=self.hospital_ch_admissions_by_age_sex_df,
            age=age,
            sex=sex,
            weight_mapper=self.ch_mapper,
        )

    def get_n_hospital_admissions(
        self, age: int, sex: str, is_care_home: bool = False
    ) -> int:
        if is_care_home:
            return self.get_care_home_hospital_admissions(age=age, sex=sex)
        else:
            return self.get_gp_hospital_admissions(age=age, sex=sex)

    def get_hospital_death_rate(
        self, age: int, sex: str, is_care_home: bool = False
    ) -> int:
        return self.get_n_hospital_deaths(
            age=age, sex=sex, is_care_home=is_care_home
        ) / self.get_n_hospital_admissions(age=age, sex=sex, is_care_home=is_care_home)

    #### home ####
    def get_all_home_deaths(self, age: int, sex: str):
        return self.get_all_deaths(age=age, sex=sex) - self.get_all_hospital_deaths(
            age=age, sex=sex
        )

    def get_care_home_home_deaths(self, age: int, sex: str):
        return self.get_n_deaths(
            age=age, sex=sex, is_care_home=True
        ) - self.get_n_hospital_deaths(age=age, sex=sex, is_care_home=True)

    def get_n_home_deaths(self, age: int, sex: str, is_care_home: bool = False):
        if is_care_home:
            return self.get_care_home_home_deaths(age=age, sex=sex)
        else:
            return self.get_n_deaths(
                age=age, sex=sex, is_care_home=False
            ) - self.get_n_hospital_deaths(age=age, sex=sex, is_care_home=False)

    #### IFRS #####
    def _get_ifr(
        self,
        function,
        age: Union[int, pd.Interval],
        sex: str,
        is_care_home: bool = False,
    ):
        if isinstance(age, pd.Interval):
            if sex == "all":
                function_values = sum(
                    function(age=agep, sex="male", is_care_home=is_care_home)
                    + function(age=agep, sex="female", is_care_home=is_care_home)
                    for agep in range(age.left, age.right + 1)
                )
                n_cases = sum(
                    self.get_n_cases(age=agep, sex="male", is_care_home=is_care_home)
                    + self.get_n_cases(
                        age=agep, sex="female", is_care_home=is_care_home
                    )
                    for agep in range(age.left, age.right + 1)
                )
            else:
                function_values = sum(
                    function(age=agep, sex=sex, is_care_home=is_care_home)
                    for agep in range(age.left, age.right + 1)
                )
                n_cases = sum(
                    self.get_n_cases(age=agep, sex=sex, is_care_home=is_care_home)
                    for agep in range(age.left, age.right + 1)
                )
        else:
            if sex == "all":
                function_values = function(
                    age=age, sex="male", is_care_home=is_care_home
                ) + function(age=age, sex="female", is_care_home=is_care_home)
                n_cases = self.get_n_cases(
                    age=age, sex="male", is_care_home=is_care_home
                ) + self.get_n_cases(age=age, sex="female", is_care_home=is_care_home)
            else:
                function_values = function(age=age, sex=sex, is_care_home=is_care_home)
                n_cases = self.get_n_cases(age=age, sex=sex, is_care_home=is_care_home)
        if n_cases * function_values == 0:
            return 0
        return function_values / n_cases

    def get_infection_fatality_rate(
        self, age: Union[int, pd.Interval], sex: str, is_care_home: bool = False
    ) -> float:
        return self._get_ifr(
            function=self.get_n_deaths, age=age, sex=sex, is_care_home=is_care_home
        )

    def get_hospital_infection_fatality_rate(
        self, age: Union[int, pd.Interval], sex: str, is_care_home: bool = False
    ) -> int:
        return self._get_ifr(
            function=self.get_n_hospital_deaths,
            age=age,
            sex=sex,
            is_care_home=is_care_home,
        )

    def get_hospital_infection_admission_rate(
        self, age: Union[int, pd.Interval], sex: str, is_care_home: bool = False
    ) -> int:
        return self._get_ifr(
            function=self.get_n_hospital_admissions,
            age=age,
            sex=sex,
            is_care_home=is_care_home,
        )

    def get_home_infection_fatality_rate(
        self, age: Union[int, pd.Interval], sex: str, is_care_home: bool = False
    ):
        return self._get_ifr(
            function=self.get_n_home_deaths, age=age, sex=sex, is_care_home=is_care_home
        )


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
                        function(age=age_bin, sex=sex, is_care_home=ch,) * 100
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
