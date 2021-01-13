import pandas as pd


class CasesDistributor:
    """
    Class to distribute cases to super areas from different
    geographic and demographic granularities.
    """

    def __init__(self, cases_per_super_area):
        self.cases_per_super_area = cases_per_super_area

    @classmethod
    def from_regional_cases(
        cls,
        cases_per_day_region: pd.DataFrame,
        super_area_to_region: pd.DataFrame,
        residents_per_super_area: pd.DataFrame,
    ):
        """
        Creats cases per super area from specifying the number of cases per region.

        Parameters
        ----------
        cases_per_day_region
            A Pandas df with date as index, regions as columns, and cases as values.
        super_area_to_region
            A df containing two columns ['super_area', 'region']
        residents_by_super_area
            A df with the number of residents per super area (index).
        """
        residents_per_super_area.set_index("super_area", inplace=True)
        ret = pd.DataFrame(index=cases_per_day_region.index)
        people_per_super_area_and_region = pd.merge(
            residents_per_super_area, super_area_to_region, on="super_area"
        )
        people_per_region = people_per_super_area_and_region.groupby("region").sum()
        super_areas = super_area_to_region.loc[
            super_area_to_region.region.isin(cases_per_day_region.columns), "super_area"
        ].values
        super_area_to_region.set_index("super_area", inplace=True)
        for super_area in super_areas:
            region = super_area_to_region.loc[super_area]
            cases_per_day = cases_per_day_region.loc[:, region]
            ret[super_area] = (
                cases_per_day
                * residents_per_super_area.loc[super_area].values
                / people_per_region.loc[region].values
            )
        return cls(ret)
