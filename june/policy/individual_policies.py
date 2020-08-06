import numpy as np
from typing import Union, Optional, List, Dict
import datetime

from .policy import Policy, PolicyCollection, Policies
from june.infection.symptom_tag import SymptomTag
from june.demography.person import Person


class IndividualPolicy(Policy):
    def __init__(
        self,
        start_time: Union[str, datetime.datetime],
        end_time: Union[str, datetime.datetime],
    ):
        super().__init__(start_time=start_time, end_time=end_time)
        self.policy_type = "individual"
        self.policy_subtype = None


class IndividualPolicies(PolicyCollection):
    policy_type = "individual"
    min_age_home_alone = 15

    def apply(self, person: Person, days_from_start: float, activities: List[str]):
        """
        Applies all active individual policies to the person. Stay home policies are applied first,
        since if the person stays home we don't need to check for the others.
        IF a person is below 15 years old, then we look for a guardian to stay with that person at home.
        """
        for policy in self.policies:
            if policy.policy_subtype == "stay_home":
                if policy.check_stay_home_condition(person, days_from_start):
                    activities = policy.apply(
                        person=person,
                        days_from_start=days_from_start,
                        activities=activities,
                    )
                    if person.age < self.min_age_home_alone:  # can't stay home alone
                        possible_guardians = [
                            housemate
                            for housemate in person.residence.group.people
                            if housemate.age >= 18
                        ]
                        if not possible_guardians:
                            guardian = person.find_guardian()
                            if guardian is not None:
                                if guardian.busy:
                                    for subgroup in guardian.subgroups.iter():
                                        if subgroup is not None and guardian in subgroup:
                                            subgroup.remove(guardian)
                                            break
                                guardian.residence.append(guardian)
                    return activities  # if it stays at home we don't need to check the rest
            elif policy.policy_subtype == "skip_activity":
                if policy.check_skips_activity(person):
                    activities = policy.apply(activities=activities)
        return activities


class StayHome(IndividualPolicy):
    """
    Template for policies that will force someone to stay at home
    """

    def __init__(self, start_time="1900-01-01", end_time="2100-01-01"):
        super().__init__(start_time=start_time, end_time=end_time)
        self.policy_subtype = "stay_home"

    def apply(self, person: Person, days_from_start: float, activities: List[str]):
        """
        Removes all activities but residence if the person has to stay at home.
        """
        if "medical_facility" in activities:
            return ["medical_facility", "residence"]
        else:
            return ["residence"]

    def check_stay_home_condition(self, person: Person, days_from_start: float):
        """
        Returns true if a person must stay at home.
        Parameters
        ----------
        person: 
            person to whom the policy is being applied

        days_from_start:
            time past from beginning of simulation, in units of days
        """
        raise NotImplementedError(
            f"Need to implement check_stay_home_condition for policy {self.__class__.__name__}"
        )


class SevereSymptomsStayHome(StayHome):

    def check_stay_home_condition(self, person: Person, days_from_start: float) -> bool:
        return (
            person.health_information is not None
            and person.health_information.tag is SymptomTag.severe
        )


class Quarantine(StayHome):
    def __init__(
        self,
        start_time: Union[str, datetime.datetime] = "1900-01-01",
        end_time: Union[str, datetime.datetime] = "2100-01-01",
        n_days: int = 7,
        n_days_household: int = 14,
        household_compliance: float = 1.0,
    ):
        """
        This policy forces people to stay at home for ```n_days``` days after they show symtpoms, and for ```n_days_household``` if someone else in their household shows symptoms

        Parameters
        ----------
        start_time:
            date at which to start applying the policy
        end_time:
            date from which the policy won't apply
        n_days:
            days for which the person has to stay at home if they show symtpoms
        n_days_household:
            days for which the person has to stay at home if someone in their household shows symptoms
        household_compliance:
            percentage of people that will adhere to the hoseuhold quarantine policy
        """
        super().__init__(start_time, end_time)
        self.n_days = n_days
        self.n_days_household = n_days_household
        self.household_compliance = household_compliance

    def check_stay_home_condition(self, person: Person, days_from_start):
        self_quarantine = False
        try:
            if person.symptoms.tag in (SymptomTag.mild, SymptomTag.severe):
                time_of_symptoms_onset = (
                    person.health_information.time_of_symptoms_onset
                )
                release_day = time_of_symptoms_onset + self.n_days
                if release_day > days_from_start > time_of_symptoms_onset:
                    self_quarantine = True
        except AttributeError:
            pass
        housemates_quarantine = person.residence.group.quarantine(
            time=days_from_start,
            quarantine_days=self.n_days_household,
            household_compliance=self.household_compliance,
        )
        return self_quarantine or housemates_quarantine


class Shielding(StayHome):
    def __init__(
        self,
        start_time: str,
        end_time: str,
        min_age: int,
        compliance: Optional[float] = None,
    ):
        super().__init__(start_time, end_time)
        self.min_age = min_age
        self.compliance = compliance

    def check_stay_home_condition(self, person: Person, days_from_start: float):
        if person.age >= self.min_age:
            if self.compliance is None or np.random.rand() < self.compliance:
                return True
        return False


class SkipActivity(IndividualPolicy):
    """
    Template for policies that will ban an activity for a person
    """

    def __init__(
        self,
        start_time: Union[str, datetime.datetime] = "1900-01-01",
        end_time: Union[str, datetime.datetime] = "2100-01-01",
        activities_to_remove=None,
    ):
        super().__init__(start_time=start_time, end_time=end_time)
        self.activities_to_remove = activities_to_remove
        self.policy_subtype = "skip_activity"

    def check_skips_activity(self, person: "Person") -> bool:
        """
        Returns True if the activity is to be skipped, otherwise False
        """
        pass

    def apply(self, activities: List[str]) -> List[str]:
        """
        Remove an activity from a list of activities

        Parameters
        ----------
        activities:
            list of activities
        activity_to_remove:
            activity that will be removed from the list
        """
        return [
            activity
            for activity in activities
            if activity not in self.activities_to_remove
        ]


class CloseSchools(SkipActivity):
    def __init__(
        self, start_time: str, end_time: str, years_to_close=None, full_closure=None,
    ):
        super().__init__(
            start_time, end_time, activities_to_remove=["primary_activity"]
        )
        self.full_closure = full_closure
        self.years_to_close = years_to_close
        if self.years_to_close == "all":
            self.years_to_close = np.arange(20)

    def _check_kid_goes_to_school(self, person: "Person"):
        """
        Checks if a kid should go to school when there is a lockdown.
        The rule is that a kid goes to school if the age is below 14 (not included)
        and there are at least two key workers at home.
        """
        if person.age < 14:
            keyworkers_parents = 0
            for person in person.residence.group.residents:
                if person.lockdown_status == "key_worker":
                    keyworkers_parents += 1
                    if keyworkers_parents > 1:
                        return True
        return False

    def check_skips_activity(self, person: "Person") -> bool:
        """
        Returns True if the activity is to be skipped, otherwise False
        """
        try:
            if person.primary_activity.group.spec == "school":
                return (
                    self.full_closure or person.age in self.years_to_close
                ) and not self._check_kid_goes_to_school(person)
        except AttributeError:
            return False
        return False


class CloseUniversities(SkipActivity):
    def __init__(
        self, start_time: str, end_time: str,
    ):
        super().__init__(
            start_time, end_time, activities_to_remove=["primary_activity"]
        )

    def check_skips_activity(self, person: "Person") -> bool:
        """
        Returns True if the activity is to be skipped, otherwise False
        """
        if (
            person.primary_activity is not None
            and person.primary_activity.group.spec == "university"
        ):
            return True
        return False


class CloseCompanies(SkipActivity):
    def __init__(
        self,
        start_time: str,
        end_time: str,
        full_closure=False,
        random_work_probability=None,
    ):
        """
        Prevents workers with the tag ``person.lockdown_status=furlough" to go to work.
        If full_closure is True, then no one will go to work.
        """
        super().__init__(start_time, end_time, ["primary_activity", "commute"])
        self.full_closure = full_closure
        self.random_work_probability = random_work_probability

    def check_skips_activity(self, person: "Person") -> bool:
        """
        Returns True if the activity is to be skipped, otherwise False
        """
        if (
            person.primary_activity is not None
            and person.primary_activity.group.spec == "company"
        ):

            if self.full_closure or person.lockdown_status == "furlough":
                return True
            elif (
                person.lockdown_status == "random"
                and self.random_work_probability is not None
            ):
                if np.random.rand() > self.random_work_probability:
                    return True
        return False

