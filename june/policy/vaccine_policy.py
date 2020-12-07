import operator
from random import random
import numpy as np
import datetime 
from june.demography.person import Person
from .policy import Policy, PolicyCollection, Policies, read_date
from june import paths

class VaccineDistribution(Policy):
    policy_type = "vaccine_distribuion"

    def __init__(
        self,
        start_time: str = "1900-01-01",
        end_time: str="2100-01-01",
        group_description: dict={'by': 'residence', 'group': 'care_home'},
        group_coverage: float=0.4,
        efficacy: float=1.,
        second_dose_compliance: float=1.,
        first_rollout_days: int=100,
        mean_time_delay: int=1,
        std_time_delay: int=1,
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
        self.group_attribute, self.group_value = self.process_group_description(group_description)
        self.group_coverage = group_coverage
        self.efficacy = efficacy
        self.second_dose_compliance = second_dose_compliance
        self.total_days = (self.end_time - self.start_time).days
        self.final_susceptibilty = 1 - efficacy
        self.vaccinated_ids = set()

    def process_group_description(self, group_description):
        if group_description["by"] in ("residence", "primary_activity"):
            return f'{group_description["by"]}.group.spec', group_description["group"]
        elif group_description["by"] == "age":
            return f'{group_description["by"]}', group_description["group"]

    def is_target_group(self, person):
        if type(self.group_value) is not list:
            try:
                if (
                    operator.attrgetter(self.group_attribute)(person)
                    == self.group_value
                ):
                    return True
            except:
                return False
        else:
            if (
                self.group_value[0]
                <= getattr(person, self.group_attribute)
                <= self.group_value[1]
            ):
                return True
        return False
        
    def apply(self, person: Person, date: datetime):
        if person.susceptibility == 1. and self.is_target_group(person):
            if random() < self.efficacy:
                if random() < self.second_dose_compliance:
                    self.vaccinate(person=person, date=date, second_dose=True)
                else:
                    self.vaccinate(person=person, date=date, second_dose=False)
                    

    def vaccinate(self, person, date, second_dose):
        person.vaccine_date = date
        person.effective_vaccine_date = date + datetime.timedelta(
            days=int(np.random.normal(loc=25, scale=10))
            ) # TODO: change this to second dose + add more necessary numbers on target sus
        self.vaccinated_ids.add(person.id)

    def susceptibility(self, time_from_vaccine, time_effective_from_vaccine):
        return 1 - time_from_vaccine/time_effective_from_vaccine

    def update_susceptibility(self, person, date):
        time_effective_from_vaccine = (person.effective_vaccine_date - person.vaccine_date).days
        person.susceptibility = self.susceptibility(
            time_from_vaccine=(date-person.vaccine_date).days,
            time_effective_from_vaccine=time_effective_from_vaccine
        )

    def update_susceptibility_of_vaccinated(self, people, date):
        if self.vaccinated_ids:
            for pid in self.vaccinated_ids:
                person = people.get_from_id(pid)
                if person.suscepbility == self.final_susceptibilty:
                    self.vaccinated_ids.remove(person)
                else:
                    self.update_susceptibility(person, date)

class VaccineDistributions(PolicyCollection):
    policy_type = "vaccine_distribution"

    def apply(self, date: datetime, person: Person):
        # before applying compliances, reset all of them to 1.0
        if self.policies:
            for region in regions:
                region.regional_compliance = 1.0
        for policy in self.policies:
            policy.apply(date=date, regions=regions)
