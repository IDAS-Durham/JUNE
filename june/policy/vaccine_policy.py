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
        first_rollout_days: int,
        mean_time_delay: int,
        std_time_delay: int,
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
        first_rollout_days: how many days will the first rollout last for
        mean_time_delay: mean time delay of the second dose being administered
        std_time_delay: std time delat of the second dose being administered

        Assumptions
        -----------
        - The chance of getting your first dose in the first first_rollout_days days is uniform
        - The probability of when you get your second dose is chosen from a Gaussian distribution
          with mean mean_time_delay and std std_time_delay
        - The vaccine is immediatrly effective after the second dose - this can be changes as needed later
        """
        
        super().__init__(start_time=start_time, end_time=end_time)
        self.group_description = group_description
        self.group_coverage = group_coverage
        self.efficacy = efficacy
        self.second_dose_compliance = second_dose_compliance
        self.total_days = (self.end_time - self.start_time).days()
        self.probabilities = self.calculate_probabilities()

    def calculate_probabilities(self):
        values = np.zeros(total_days)
        for i in range(days):
            vals = np.random.normal(loc=mean+i,scale=std,size=len(values))
            val_ints = np.round(vals)
            for j in val_ints:
                values[int(j)] += 1
        probs = values/np.sum(values)

        return probs
        

    def apply(self, date: datetime, person: Person):
        date = read_date(date)
        if self.is_active(date):
            days_from_start = int(date - self.start_date).days()
            
            if (
                self.group_description == "care_home_residents"
                and person.residence.group.spec == 'care_home'
            ):
                
                if randon() < self.probabilities[days_from_start]:
                    person.vaccinated = True

            else:
                try:
                    if(
                        person.age < int(self.group_description.split('-')[1])
                        and person.age > int(self.group_description.split('-')[0])
                    ):
                        if randon() < self.probabilities[days_from_start]:
                            person.vaccinated = True
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
