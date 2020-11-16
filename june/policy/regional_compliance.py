from datetime import datetime

from .policy import Policy, PolicyCollection, Policies, read_date
from june.geography import Regions
from june import paths


class RegionalCompliance(Policy):
    policy_type = "regional_compliance"

    def __init__(
        self, start_time: str, end_time: str, compliances_per_region: dict,
    ):
        super().__init__(start_time=start_time, end_time=end_time)
        self.compliances_per_region = compliances_per_region

    def apply(self, date: datetime, regions: Regions):
        date = read_date(date)
        if self.is_active(date):
            for region in regions:
                region.regional_compliance = self.compliances_per_region[region.name]


class RegionalCompliances(PolicyCollection):
    policy_type = "regional_compliance"

    def apply(self, date: datetime, regions: Regions):
        # before applying compliances, reset all of them to 1.0
        if self.policies:
            for region in regions:
                region.regional_compliance = 1.0
        for policy in self.policies:
            policy.apply(date=date, regions=regions)
