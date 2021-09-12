from datetime import datetime

from .policy import Policy, PolicyCollection, Policies, read_date
from june.geography import Regions
from june import paths


class RegionalCompliance(Policy):
    policy_type = "regional_compliance"

    def __init__(
        self,
        start_time: str,
        end_time: str,
        compliances_per_region: dict,
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


class TieredLockdown(Policy):
    policy_type = "tiered_lockdown"

    def __init__(
        self,
        start_time: str,
        end_time: str,
        tiers_per_region: dict,
    ):
        super().__init__(start_time=start_time, end_time=end_time)
        self.tiers_per_region = tiers_per_region

    def apply(self, date: datetime, regions: Regions):
        date = read_date(date)
        if self.is_active(date):
            for region in regions:
                lockdown_tier = int(self.tiers_per_region[region.name])
                region.policy["lockdown_tier"] = lockdown_tier
                if lockdown_tier == 2:
                    region.policy["local_closed_venues"].update("residence_visits")
                elif lockdown_tier == 3:
                    region.policy["local_closed_venues"].update(
                        set(("cinema", "residence_visits"))
                    )
                elif lockdown_tier == 4:
                    region.policy["local_closed_venues"].update(
                        set(("pub", "cinema", "gym", "residence_visits"))
                    )


class TieredLockdowns(PolicyCollection):
    policy_type = "tiered_lockdown"

    def apply(self, date: datetime, regions: Regions):
        # before applying compliances, reset all of them to None and empty sets
        if self.policies:
            for region in regions:
                region.policy["lockdown_tier"] = None
                region.policy["local_closed_venues"] = set()
        for policy in self.policies:
            policy.apply(date=date, regions=regions)
