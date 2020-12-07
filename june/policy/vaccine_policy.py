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
        group_coverage: float=1.,
        group_prevalence: float=0.,
        efficacy: float=1.,
        second_dose_compliance: float=1.,
        mean_time_delay: int=1,
        std_time_delay: int=1,
        effective_after_first_dose: int=7,
        effective_after_second_dose: int=7,
    ):
        """
        Policy to apply a vaccinated tag to people based on certain attributes with a given probability

        Parameters
        ----------
        start_time: start time of vaccine rollout
        end_time: end time of vaccine rollout
        group_description: type of people to get the vaccine, currently support:
            by: either residence, primary activity or age
            group: group type e.g. care_home for residence or XX-YY for age range
        group_coverage: % of group to be left as having target susceptibility after vaccination
        group_prevalence: the prevalence level in the group at time of vaccination rollout
        efficacy: % of people vaccinated who get the vaccinated tag
        second_dose_compliance: % of people getting their second vaccine dose if required
        mean_time_delay: mean time delay of the second dose being administered
        std_time_delay: std time delat of the second dose being administered
        effective_after_first_dose: number of days for the first dose to become effective
        effective_after_second_dose: number of days for second dose to become effective

        Assumptions
        -----------
        - The chance of getting your first dose in the first first_rollout_days days is uniform
        - The probability of when you get your second dose is chosen from a Gaussian distribution
          with mean mean_time_delay and std std_time_delay
        - The progression over time after vaccination (first and/or second dose) to reach the target
          susceptibilty is linear
        - The target susceptiblity after the first dose is half that of after the second dose
        - The target susceptibility after the second dose is 1-efficacy of the vaccine
        """
        
        super().__init__(start_time=start_time, end_time=end_time)
        self.total_days = (self.end_time - self.start_time).days
        self.group_attribute, self.group_value = self.process_group_description(group_description)
        self.group_coverage = group_coverage
        self.group_prevalence = group_prevalence
        self.second_dose_compliance = second_dose_compliance
        self.mean_time_delay = mean_time_delay
        self.std_time_delay = std_time_delay
        self.effective_after_first_dose = effective_after_first_dose
        self.effective_after_second_dose = effective_after_second_dose
        self.final_susceptibilty = 1 - efficacy
        self.vaccinated_ids = set()

    def process_group_description(self, group_description):
        if group_description["by"] in ("residence", "primary_activity"):
            return f'{group_description["by"]}.group.spec', group_description["group"]
        elif group_description["by"] == "age":
            return f'{group_description["by"]}', group_description["group"]
        
    def vaccinate(self, person, date):
        # first dose
        person.first_effective_date = date + datetime.timedelta(days=self.effective_after_first_dose)

        # second dose
        if random() < self.second_dose_compliance:
            second_dose_date = date + datetime.timedelta(
                days=int(np.random.normal(loc=self.mean_time_delay, scale=self.std_time_delay))
            )
            second_effective_date = second_dose_date + datetime.timedelta(days=self.effective_after_second_dose)
        else:
            second_dose_date = None
            second_effective_date = None
        person.second_dose_date = second_dose_date
        person.second_effective_date = second_effective_date

        self.vaccinated_ids.add(person.id)

    def is_target_group(self, person):
        if self.group_attribute is not "age":
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
                int(self.group_value.split('-')[0])
                <= getattr(person, self.group_attribute)
                <= int(self.group_value.split('-')[1])
            ):
                return True
        return False

    def apply(self, date: datetime, person: Person):
        if person.susceptibility == 1. and self.is_target_group(person):
            print ("Passing")
            days_passed = (date - self.start_time).days
            if random() < (self.group_coverage-self.group_prevalence)*(1/(self.total_days-days_passed)):
                self.vaccinate(person=person, date=date)                    

        
    def susceptibility(self, time_vaccine_effect, vaccine_target, susceptibility):
        
        # ensure target susceptibility is reached and avoid rounding errors
        if time_vaccine_effect == 0:
            return vaccine_target
        else:
            return susceptibility + (vaccine_target-susceptibilty)/time_vaccine_effect

    def update_susceptibility(self, person, date):

        # update for first dose
        if person.susceptiblity <= self.final_susceptibility/2.:
            time_vaccine_effect = (person.first_effective_date - date).days
            person.susceptibility = self.susceptibility(
                time_vaccine_effect=time_vaccine_effect,
                vaccine_target = self.final_susceptibility/2.,
                susceptibility = person.susceptibility
            )

        # update second dose
        else:
            # if they will have the second dose
            if person.second_dose_date is not None:
                # and they have already had it
                if person.second_dose_date < date:
                    pass
                else:
                    time_vaccine_effect = (person.second_effective_date - date).days
                    person.susceptibility = self.susceptibility(
                        time_vaccine_effect=time_vaccine_effect,
                        vaccine_target = self.final_susceptibility,
                        susceptibility = person.susceptibility
                    )
            else:
                self.vaccinated_ids.remove(person)

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
        if self.policies:
            for policy in self.policies:
                policy.apply(date=date, person=person)
