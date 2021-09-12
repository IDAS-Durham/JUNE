import pandas as pd
import numpy as np

from june import paths

default_super_area_to_region_file = (
    paths.data_path / "input/geography/area_super_area_region.csv"
)
default_residents_per_super_area_file = (
    paths.data_path / "input/demography/residents_per_super_area.csv"
)


def get_super_area_population_weights_by_region(
    super_area_to_region: pd.DataFrame, residents_per_super_area: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute the weight in population that a super area has over its whole region, used
    to convert regional cases to cases by super area by population density

    Returns
    -------
    data frame indexed by super area, with weights and region
    """
    people_per_super_area_and_region = pd.merge(
        residents_per_super_area, super_area_to_region, on="super_area",
    )
    people_per_region = people_per_super_area_and_region.groupby("region").sum()[
        "n_residents"
    ]
    people_per_super_area_and_region[
        "weights"
    ] = people_per_super_area_and_region.apply(
        lambda x: x.n_residents / people_per_region.loc[x.region], axis=1
    )
    ret = people_per_super_area_and_region.loc[:, ["super_area", "weights"]]
    ret = ret.set_index("super_area")
    return ret


def get_super_area_population_weights(
    residents_per_super_area: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute the weight in population that a super area has over its whole region, used
    to convert regional cases to cases by super area by population density

    Returns
    -------
    data frame indexed by super area, with weights and region
    """
    residents_per_super_area.set_index("super_area", inplace=True)

    percent = residents_per_super_area / residents_per_super_area["n_residents"].sum()
    return percent


class CasesDistributor:
    """
    Class to distribute cases to super areas from different
    geographic and demographic granularities.
    """

    def __init__(self, cases_per_super_area):
        cases_per_super_area.index = pd.to_datetime(cases_per_super_area.index)
        self.cases_per_super_area = cases_per_super_area

    @classmethod
    def from_regional_cases(
        cls,
        cases_per_day_region: pd.DataFrame,
        super_area_to_region: pd.DataFrame,
        residents_per_super_area: pd.DataFrame,
    ):
        """
        Creates cases per super area from specifying the number of cases per region.

        Parameters
        ----------
        cases_per_day_region
            A Pandas df with date as index, regions as columns, and cases as values.
        super_area_to_region
            A df containing two columns ['super_area', 'region']
        residents_per_super_area
            A df with the number of residents per super area (index).
        """
        residents_per_super_area.set_index("super_area", inplace=True)
        ret = pd.DataFrame(index=cases_per_day_region.index)
        weights_per_super_area = get_super_area_population_weights_by_region(
            super_area_to_region=super_area_to_region,
            residents_per_super_area=residents_per_super_area,
        )
        for region in cases_per_day_region.columns:
            region_cases = cases_per_day_region.loc[:, region]
            region_super_areas = super_area_to_region.loc[
                super_area_to_region.region == region, "super_area"
            ]
            ret.loc[:, region_super_areas] = 0
            for date, n_cases in region_cases.iteritems():
                weights = weights_per_super_area.loc[
                    region_super_areas
                ].values.flatten()
                cases_distributed = np.random.choice(
                    region_super_areas, size=n_cases, p=weights, replace=True
                )
                super_areas, cases = np.unique(cases_distributed, return_counts=True)
                ret.loc[date, super_areas] = cases
        return cls(ret)

    @classmethod
    def from_regional_cases_file(
        cls,
        cases_per_day_region_file: str,
        super_area_to_region_file: str = default_super_area_to_region_file,
        residents_per_super_area_file: str = default_residents_per_super_area_file,
    ):
        cases_per_day_region = pd.read_csv(cases_per_day_region_file, index_col=0)
        super_area_to_region = pd.read_csv(super_area_to_region_file)
        super_area_to_region = super_area_to_region.loc[
            :, ["super_area", "region"]
        ].drop_duplicates()
        residents_per_super_area = pd.read_csv(residents_per_super_area_file)
        return cls.from_regional_cases(
            cases_per_day_region=cases_per_day_region,
            super_area_to_region=super_area_to_region,
            residents_per_super_area=residents_per_super_area,
        )

    @classmethod
    def from_national_cases(
        cls,
        cases_per_day: pd.DataFrame,
        super_area_to_region: pd.DataFrame,
        residents_per_super_area: pd.DataFrame,
    ):
        ret = pd.DataFrame(index=cases_per_day.index)
        weights_per_super_area = get_super_area_population_weights(
            residents_per_super_area=residents_per_super_area,
        )
        for date, n_cases in cases_per_day.iterrows():
            weights = weights_per_super_area.values.flatten()
            cases_distributed = np.random.choice(
                list(weights_per_super_area.index),
                size=n_cases.values[0],
                p=weights,
                replace=True,
            )
            super_areas, cases = np.unique(cases_distributed, return_counts=True)
            ret.loc[date, super_areas] = cases
        return cls(ret)

    @classmethod
    def from_national_cases_file(
        cls,
        cases_per_day_file,
        super_area_to_region_file: str = default_super_area_to_region_file,
        residents_per_super_area_file: str = default_residents_per_super_area_file,
    ):
        cases_per_day = pd.read_csv(cases_per_day_file, index_col=0)
        residents_per_super_area = pd.read_csv(residents_per_super_area_file)
        super_area_to_region = pd.read_csv(super_area_to_region_file)
        super_area_to_region = super_area_to_region.loc[
            :, ["super_area", "region"]
        ].drop_duplicates()

        return cls.from_national_cases(
            cases_per_day=cases_per_day,
            super_area_to_region=super_area_to_region,
            residents_per_super_area=residents_per_super_area,
        )
