from datetime import datetime

from june.demography.person import Person
from .policy import Policy, PolicyCollection, Policies, read_date
from june import paths

class VaccineDistribution(Policy):
    policy_type = "vaccine_distribuion"

    def __init__(
        self,
        start_time: str,
        end_time: str,
        group_description: str,
        group_coverage: int,
        efficacy: float,
        second_dose_compliance: float,
        time_delay: float,
    ):
        """
        Policy to apply a vaccinated tag to people based on certain attributes with a given probability

        Parameters
        ----------
        start_time: start time of vaccine rollout
        end_time: end time of vaccine rollout
        group_description: type of people to get the vaccine, currently support:
            - care_home_residents
            - XX-YY where XX and YY denote an age range
        group_coverage: % of group to be vaccinated over the rollout period
        efficacy: % of people vaccinated who get the vaccinated tag
        second_dose_compliance: % of people getting their second vaccine dose if required
        time_delay: the parameter of the time delay distribution
        """
        
        super().__init__(start_time=start_time, end_time=end_time)
        self.group_description = group_description
        self.group_coverage = group_coverage
        self.efficacy = efficacy
        self.second_dose_compliance = second_dose_compliance


    def apply(self, date: datetime, person: Person):
        date = read_date(date)
        if self.is_active(date):
            if (
                self.group_description == "care_home_residents"
                and person.???
            ):

            else:
                try:
                    if(
                        person.age < int(self.group_description.split('-')[1])
                        and person.age > int(self.group_description.split('-')[0])
                    ):
                        
                except:
                    raise ValueError(f"vaccine policy group_description type not valid")


class VaccineDistributions(PolicyCollection):
    policy_type = "vaccine_distribution"

    def apply(self, date: datetime, person: Person):
        # before applying compliances, reset all of them to 1.0
        if self.policies:
            for region in regions:
                region.regional_compliance = 1.0
        for policy in self.policies:
            policy.apply(date=date, regions=regions)
