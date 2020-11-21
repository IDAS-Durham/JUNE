import pandas as pd
from june import paths

default_seroprevalence_file = (
    paths.data_path / "input/health_index/seroprevalence_by_age_imperial.csv"
)
default_population_file = (
    paths.data_path / "input/health_index/population_by_age_2020_ew.csv"
)


def convert_to_intervals(age: str) -> pd.Interval:
    return pd.Interval(
        left=int(age.split("-")[0]), right=int(age.split("-")[1]), closed="both"
    )


class Data2Rates:
    def __init__(
        self, seroprevalence_df: pd.DataFrame, population_by_age_sex_df: pd.DataFrame
    ):
        self.seroprevalence_df = seroprevalence_df
        self.population_by_age_sex_df = population_by_age_sex_df

    @classmethod
    def from_files(
        cls,
        seroprevalence_file: str = default_seroprevalence_file,
        population_file: str = default_population_file,
    ) -> "Data2Rates":

        seroprevalence_df = pd.read_csv(
            default_seroprevalence_file, converters={"age": convert_to_intervals}
        )
        seroprevalence_df.set_index("age", inplace=True)
        population_df = pd.read_csv(population_file)
        population_df.set_index("age", inplace=True)
        return cls(
            seroprevalence_df=seroprevalence_df, population_by_age_sex_df=population_df
        )

    def n_cases(self, age):
        pass


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
        x=[(index.left + index.right) / 2 for index in ifr_ward.index],
        height=ifr_ward[0].values,
        width=[index.right - index.left for index in ifr_ward.index],
        alpha=0.4,
        label="Ward",
    )
    plt.bar(
        x=[(index.left + index.right) / 2 for index in ifr_imperial.index],
        height=ifr_imperial[0].values,
        width=[index.right - index.left for index in ifr_imperial.index],
        alpha=0.4,
        label="Imperial",
    )
    plt.legend()
    plt.ylabel("Death rate")
    plt.xlabel("Age")
    plt.show()
