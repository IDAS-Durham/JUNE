import logging
import pandas as pd
import numpy as np
from typing import List, Union, Optional
from june import paths
import yaml


# ch = care home, gp = general population (so everyone not in a care home)

hi_data = paths.data_path / "input/health_index"
default_seroprevalence_file = hi_data / "seroprevalence_by_age.csv"
default_care_home_seroprevalence_file = hi_data / "care_home_seroprevalence_by_age.csv"

default_population_file = hi_data / "population_by_age_sex_2020_england.csv"
default_care_home_population_file = hi_data / "care_home_residents_by_age_sex_june.csv"

default_all_deaths_file = hi_data / "all_deaths_by_age_sex.csv"
default_care_home_deaths_file = hi_data / "care_home_deaths_by_age_sex.csv"
default_all_hospital_deaths_file = hi_data / "hospital_deaths_by_age_sex.csv"
default_all_hospital_admissions_file = hi_data / "hospital_admissions_by_age_sex.csv"
default_gp_admissions_file = hi_data / "cocin_gp_hospital_admissions_by_age_sex.csv"
default_ch_admissions_file = hi_data / "chess_ch_hospital_admissions_by_age_sex.csv"
default_gp_hospital_deaths_file = hi_data / "cocin_gp_hospital_deaths_by_age_sex.csv"
default_ch_hospital_deaths_file = hi_data / "chess_ch_hospital_deaths_by_age_sex.csv"
default_icu_hosp_rate_file = hi_data / "icu_hosp_rate.csv"
default_deathsicu_deathshosp_rate_file = hi_data / "dicu_dhosp_rate.csv"
default_asymptomatic_rate_file = hi_data / "asymptomatic_rates_by_age_sex.csv"
default_mild_rate_file = hi_data / "mild_rates_by_age_sex.csv"

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
        hospital_all_deaths_by_age_sex_df: pd.DataFrame,
        hospital_all_admissions_by_age_sex_df: pd.DataFrame,
        hospital_gp_deaths_by_age_sex_df: pd.DataFrame,
        hospital_ch_deaths_by_age_sex_df: pd.DataFrame,
        hospital_gp_admissions_by_age_sex_df: pd.DataFrame,
        hospital_ch_admissions_by_age_sex_df: pd.DataFrame,
        care_home_deaths_by_age_sex_df: pd.DataFrame = None,
        care_home_seroprevalence_by_age_df: pd.DataFrame = None,
        icu_hosp_rate_by_age_sex_df: pd.DataFrame = None,
        deathsicu_deathshosp_rate_by_age_df: pd.DataFrame = None,
        comorbidity_multipliers: Optional[dict] = None,
        comorbidity_prevalence_reference_population: Optional[dict] = None,
        asymptomatic_rates_by_age_sex_df: pd.DataFrame = None,
        mild_rates_by_age_sex_df: pd.DataFrame = None,
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
        self.care_home_population_by_age_sex_df = self._process_df(
            care_home_population_by_age_sex_df, converters=False
        )
        self.all_deaths_by_age_sex_df = self._process_df(
            all_deaths_by_age_sex_df, converters=True
        )
        self.care_home_deaths_by_age_sex_df = self._process_df(
            care_home_deaths_by_age_sex_df, converters=True
        )
        self.all_hospital_deaths_by_age_sex = self._process_df(
            hospital_all_deaths_by_age_sex_df, converters=True
        )
        self.all_hospital_admissions_by_age_sex = self._process_df(
            hospital_all_admissions_by_age_sex_df, converters=True
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
        self.icu_hosp_rate_by_age_sex_df = self._process_df(
            icu_hosp_rate_by_age_sex_df, converters=False
        )
        self.deathsicu_deathshosp_rate_by_age_df = self._process_df(
            deathsicu_deathshosp_rate_by_age_df, converters=False
        )
        self.comorbidity_multipliers = comorbidity_multipliers
        self.comorbidity_prevalence_reference_population = (
            comorbidity_prevalence_reference_population
        )
        self.mild_rates_by_age_sex_df = self._process_df(
            mild_rates_by_age_sex_df, converters=True
        )
        self.asymptomatic_rates_by_age_sex_df = self._process_df(
            asymptomatic_rates_by_age_sex_df, converters=True
        )
        self._init_mappers()

    @classmethod
    def from_file(
        cls,
        seroprevalence_file: str = default_seroprevalence_file,
        care_home_seroprevalence_by_age_file: str = default_care_home_seroprevalence_file,
        population_file: str = default_population_file,
        care_home_population_file: str = default_care_home_population_file,
        all_deaths_file: str = default_all_deaths_file,
        all_hospital_deaths_file: str = default_all_hospital_deaths_file,
        all_hospital_admissions_file: str = default_all_hospital_admissions_file,
        hospital_gp_deaths_file: str = default_gp_hospital_deaths_file,
        hospital_ch_deaths_file: str = default_ch_hospital_deaths_file,
        hospital_gp_admissions_file: str = default_gp_admissions_file,
        hospital_ch_admissions_file: str = default_ch_admissions_file,
        icu_hosp_rate_file: str = default_icu_hosp_rate_file,
        deathsicu_deathshosp_rate_file: str = default_deathsicu_deathshosp_rate_file,
        care_home_deaths_file: str = default_care_home_deaths_file,
        asymptomatic_rates_file: str = default_asymptomatic_rate_file,
        mild_rates_file: str = default_mild_rate_file,
        comorbidity_multipliers_file: Optional[str] = None,
        comorbidity_prevalence_female_file: Optional[str] = None,
        comorbidity_prevalence_male_file: Optional[str] = None,
    ) -> "Data2Rates":

        seroprevalence_df = cls._read_csv(seroprevalence_file)
        population_df = cls._read_csv(population_file)
        all_deaths_df = cls._read_csv(all_deaths_file)
        hospital_gp_deaths_df = cls._read_csv(hospital_gp_deaths_file)
        hospital_ch_deaths_df = cls._read_csv(hospital_ch_deaths_file)
        hospital_all_deaths_df = cls._read_csv(all_hospital_deaths_file)
        hospital_all_admissions_df = cls._read_csv(all_hospital_admissions_file)
        hospital_gp_admissions_df = cls._read_csv(hospital_gp_admissions_file)
        hospital_ch_admissions_df = cls._read_csv(hospital_ch_admissions_file)
        mild_rates_df = cls._read_csv(mild_rates_file)
        asymptomatic_rates_df = cls._read_csv(asymptomatic_rates_file)
        icu_hosp_rate_df = cls._read_csv(icu_hosp_rate_file)
        deathsicu_deathshosp_rate_df = cls._read_csv(deathsicu_deathshosp_rate_file)

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
            with open(comorbidity_multipliers_file) as f:
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
            hospital_all_deaths_by_age_sex_df=hospital_all_deaths_df,
            hospital_all_admissions_by_age_sex_df=hospital_all_admissions_df,
            hospital_gp_deaths_by_age_sex_df=hospital_gp_deaths_df,
            hospital_ch_deaths_by_age_sex_df=hospital_ch_deaths_df,
            hospital_gp_admissions_by_age_sex_df=hospital_gp_admissions_df,
            hospital_ch_admissions_by_age_sex_df=hospital_ch_admissions_df,
            icu_hosp_rate_by_age_sex_df=icu_hosp_rate_df,
            deathsicu_deathshosp_rate_by_age_df=deathsicu_deathshosp_rate_df,
            care_home_deaths_by_age_sex_df=care_home_deaths_df,
            care_home_seroprevalence_by_age_df=care_home_seroprevalence_by_age_df,
            asymptomatic_rates_by_age_sex_df=asymptomatic_rates_df,
            mild_rates_by_age_sex_df=mild_rates_df,
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

    def _init_mappers(self):
        """
        These mappers (age, sex) -> float are used to weight bins.
        """
        self.gp_mapper = (
            lambda age, sex: self.population_by_age_sex_df.loc[age, sex]
            - self.care_home_population_by_age_sex_df.loc[age, sex]
        )
        self.ch_mapper = lambda age, sex: self.care_home_population_by_age_sex_df.loc[
            age, sex
        ]
        self.all_mapper = lambda age, sex: self.population_by_age_sex_df.loc[age, sex]
        self.gp_deaths_mapper = lambda age, sex: self.get_n_deaths(
            age=age, sex=sex, is_care_home=False
        )
        self.ch_deaths_mapper = lambda age, sex: self.get_n_deaths(
            age=age, sex=sex, is_care_home=True
        )
        self.all_deaths_mapper = lambda age, sex: self.gp_deaths_mapper(
            age, sex
        ) + self.ch_deaths_mapper(age, sex)

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
            weight_mapper=self.all_mapper,
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
        return self._get_interpolated_value(
            df=self.all_hospital_deaths_by_age_sex,
            age=age,
            sex=sex,
            weight_mapper=self.all_deaths_mapper,
        )

    def get_icu_hospital_rate(self, age: int, sex: str):
        return self.icu_hosp_rate_by_age_sex_df.loc[age, sex]

    def get_deathsicu_deathshosp_rate(self, age: int, sex: str):
        return self.deathsicu_deathshosp_rate_by_age_df.loc[age, sex]

    def get_gp_hospital_deaths(self, age: int, sex: str):
        return self.get_all_hospital_deaths(
            age=age, sex=sex
        ) - self.get_care_home_hospital_deaths(age=age, sex=sex)

    def get_care_home_hospital_deaths(self, age: int, sex: str):
        return self._get_interpolated_value(
            df=self.hospital_ch_deaths_by_age_sex_df,
            age=age,
            sex=sex,
            weight_mapper=self.ch_deaths_mapper,
        )

    def get_n_hospital_deaths(
        self, age: int, sex: str, is_care_home: bool = False
    ) -> int:
        if is_care_home:
            return self.get_care_home_hospital_deaths(age=age, sex=sex)
        else:
            return self.get_gp_hospital_deaths(age=age, sex=sex)

    def get_all_hospital_admissions(self, age: int, sex: str):
        return self._get_interpolated_value(
            df=self.all_hospital_admissions_by_age_sex,
            age=age,
            sex=sex,
            weight_mapper=self.all_deaths_mapper,
        )

    def get_gp_hospital_admissions(self, age: int, sex: str):
        return self.get_all_hospital_admissions(
            age=age, sex=sex
        ) - self.get_care_home_hospital_admissions(age=age, sex=sex)

    def get_care_home_hospital_admissions(self, age: int, sex: str):
        return self._get_interpolated_value(
            df=self.hospital_ch_admissions_by_age_sex_df,
            age=age,
            sex=sex,
            weight_mapper=self.ch_deaths_mapper,
        )

    def get_n_hospital_admissions(
        self, age: int, sex: str, is_care_home: bool = False
    ) -> int:
        if is_care_home:
            return self.get_care_home_hospital_admissions(age=age, sex=sex)
        else:
            return self.get_gp_hospital_admissions(age=age, sex=sex)

    def get_n_icu_admissions(
        self, age: int, sex: str, is_care_home: bool = False
    ) -> int:

        if is_care_home:
            return self.get_care_home_hospital_admissions(
                age=age, sex=sex
            ) * self.get_icu_hospital_rate(age=age, sex=sex)
        else:
            return self.get_gp_hospital_admissions(
                age=age, sex=sex
            ) * self.get_icu_hospital_rate(age=age, sex=sex)

    def get_n_icu_deaths(self, age: int, sex: str, is_care_home: bool = False) -> int:

        return self.get_n_hospital_deaths(
            age=age, sex=sex, is_care_home=is_care_home
        ) * self.get_deathsicu_deathshosp_rate(age=age, sex=sex)

    def get_hospital_death_rate(
        self, age: int, sex: str, is_care_home: bool = False
    ) -> int:
        return self.get_n_hospital_deaths(
            age=age, sex=sex, is_care_home=is_care_home
        ) / self.get_n_hospital_admissions(age=age, sex=sex, is_care_home=is_care_home)

    def get_icu_death_rate(self, age: int, sex: str, is_care_home: bool = False) -> int:
        return self.get_n_icu_deaths(
            age=age, sex=sex, is_care_home=is_care_home
        ) / self.get_n_icu_admissions(age=age, sex=sex, is_care_home=is_care_home)

    #### home ####
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
        return max(function_values / n_cases, 0)

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

    def get_icu_infection_fatality_rate(
        self, age: Union[int, pd.Interval], sex: str, is_care_home: bool = False
    ) -> int:
        return self._get_ifr(
            function=self.get_n_icu_deaths,
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

    def get_icu_infection_admission_rate(
        self, age: Union[int, pd.Interval], sex: str, is_care_home: bool = False
    ) -> int:
        return self._get_ifr(
            function=self.get_n_icu_admissions,
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

    def get_mild_rate(self, age: Union[int, pd.Interval], sex: str, is_care_home):
        if isinstance(age, pd.Interval):
            return self.mild_rates_by_age_sex_df.loc[age.left : age.right, sex].mean()
        else:
            return self.mild_rates_by_age_sex_df.loc[age, sex]

    def get_asymptomatic_rate(self, age: Union[int, pd.Interval], sex: str, is_care_home):
        if isinstance(age, pd.Interval):
            return self.asymptomatic_rates_by_age_sex_df.loc[
                age.left : age.right, sex
            ].mean()
        else:
            return self.mild_rates_by_age_sex_df.loc[age, sex]


def get_outputs_df(rates, age_bins):
    outputs = pd.DataFrame(
        index=age_bins,
    )
    for pop in ["gp", "ch"]:
        for sex in ["male", "female"]:
            for fname, function in zip(
                [
                    "asymptomatic",
                    "mild",
                    "ifr",
                    "hospital_ifr",
                    "icu_ifr",
                    "hospital",
                    "icu",
                    "home_ifr",
                ],
                [
                    rates.get_asymptomatic_rate,
                    rates.get_mild_rate,
                    rates.get_infection_fatality_rate,
                    rates.get_hospital_infection_fatality_rate,
                    rates.get_icu_infection_fatality_rate,
                    rates.get_hospital_infection_admission_rate,
                    rates.get_icu_infection_admission_rate,
                    rates.get_home_infection_fatality_rate,
                ],
            ):
                colname = f"{pop}_{fname}_{sex}"
                for age_bin in age_bins:
                    outputs.loc[age_bin, colname] = (
                        function(age=age_bin, sex=sex, is_care_home=pop == "ch")
                    )
    return outputs
