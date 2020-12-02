from june.geography import Region, Regions
from june.policy import RegionalCompliance, RegionalCompliances


class TestSetRegionCompliance:
    def test__set_compliance_to_region(self):
        regional_compliance = RegionalCompliance(
            start_time="2020-05-01",
            end_time="2020-09-01",
            compliances_per_region={"London": 1.5},
        )
        regional_compliances = RegionalCompliances([regional_compliance])
        region = Region(name="London")
        regions = Regions([region])
        regional_compliances.apply(regions=regions, date = "2020-05-05")
        assert region.regional_compliance == 1.5
        regional_compliances.apply(regions=regions, date = "2020-05-01")
        assert region.regional_compliance == 1.5
        regional_compliances.apply(regions=regions, date = "2020-01-05")
        assert region.regional_compliance == 1.0
        regional_compliances.apply(regions=regions, date = "2021-01-05")
        assert region.regional_compliance == 1.0
        regional_compliances.apply(regions=regions, date = "2020-09-01")
        assert region.regional_compliance == 1.0

