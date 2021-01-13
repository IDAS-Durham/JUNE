import pandas as pd
import numpy as np
from pytest import fixture

from june.infection_seed import CasesDistributor


class TestCasesDistributor:
    @fixture(name="super_area_region")
    def make_super_area_region(self):
        data = [
            ["a1", "East of England"],
            ["a2", "East of England"],
        ]
        ret = pd.DataFrame(data=data, columns=["super_area", "region"])
        return ret

    @fixture(name="residents_by_super_area")
    def make_area_super_area_region(self):
        data = [
            ["a1", 100],
            ["a2", 200],
        ]
        ret = pd.DataFrame(data=data, columns=["super_area", "n_residents"])
        return ret

    @fixture(name="cases_per_region_per_day")
    def make_cases_per_region_per_day(self):
        index = ["2020-03-01", "2020-03-02"]
        ret = pd.DataFrame(index=index)
        ret["East of England"] = [60, 120]
        return ret

    def test__from_regional_cases(
        self, super_area_region, residents_by_super_area, cases_per_region_per_day
    ):

        cd = CasesDistributor.from_regional_cases(
            cases_per_day_region=cases_per_region_per_day,
            super_area_to_region=super_area_region,
            residents_per_super_area=residents_by_super_area,
        )
        cases_per_super_area = cd.cases_per_super_area
        assert (
            cases_per_super_area.loc[:, "a1"] == np.array([20, 40], dtype=np.float)
        ).all()
        assert (
            cases_per_super_area.loc[:, "a2"] == np.array([40, 80], dtype=np.float)
        ).all()
