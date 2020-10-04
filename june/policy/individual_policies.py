import numpy as np
from typing import List, Optional, Union
import datetime
from random import random
import june.policy

from june.infection.symptom_tag import SymptomTag
from june.demography.person import Person
from june.policy import Policy, PolicyCollection
from june.mpi_setup import mpi_rank


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

    def get_active(self, date: datetime.date):
        return IndividualPolicies(
            [policy for policy in self.policies if policy.is_active(date)]
        )

    def apply(
        self,
        active_policies,
        person: Person,
        days_from_start: float,
        activities: List[str],
        furlough_ratio=None,
        key_ratio=None,
        random_ratio=None,
    ):
        """
        Applies all active individual policies to the person. Stay home policies are applied first,
        since if the person stays home we don't need to check for the others.
        IF a person is below 15 years old, then we look for a guardian to stay with that person at home.
        """
        for policy in active_policies:
            if policy.policy_subtype == "stay_home":
                if policy.check_stay_home_condition(person, days_from_start):
                    activities = policy.apply(
                        person=person,
                        days_from_start=days_from_start,
                        activities=activities,
                    )
                    # TODO: make it work with parallelisation
                    if mpi_rank == 0:
                        if (
                            person.age < self.min_age_home_alone
                        ):  # can't stay home alone
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
                                            if (
                                                subgroup is not None
                                                and guardian in subgroup
                                            ):
                                                subgroup.remove(guardian)
                                                break
                                    guardian.residence.append(guardian)
                    return activities  # if it stays at home we don't need to check the rest
            elif policy.policy_subtype == "skip_activity":
                if policy.spec == "close_companies":
                    if policy.check_skips_activity(
                        person, furlough_ratio, key_ratio, random_ratio
                    ):
                        activities = policy.apply(activities=activities)
                else:
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
            person.infection is not None and person.infection.tag is SymptomTag.severe
        )


class Quarantine(StayHome):
    def __init__(
        self,
        start_time: Union[str, datetime.datetime] = "1900-01-01",
        end_time: Union[str, datetime.datetime] = "2100-01-01",
        n_days: int = 7,
        n_days_household: int = 14,
        compliance: float = 1.0,
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
        compliance:
            percentage of symptomatic people that will adhere to the quarantine policy
        household_compliance:
            percentage of people that will adhere to the hoseuhold quarantine policy
        """
        super().__init__(start_time, end_time)
        self.n_days = n_days
        self.n_days_household = n_days_household
        self.compliance = compliance
        self.household_compliance = household_compliance
        self.compliance = compliance

    def check_stay_home_condition(self, person: Person, days_from_start):
        self_quarantine = False
        try:
            if person.symptoms.tag in (SymptomTag.mild, SymptomTag.severe):
                time_of_symptoms_onset = person.infection.time_of_symptoms_onset
                release_day = time_of_symptoms_onset + self.n_days
                if release_day > days_from_start > time_of_symptoms_onset:
                    if random() < self.compliance:
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
            if self.compliance is None or random() < self.compliance:
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
        self,
        start_time: str,
        end_time: str,
        years_to_close=None,
        attending_compliance=1.0,
        full_closure=None,
    ):
        super().__init__(
            start_time, end_time, activities_to_remove=["primary_activity"]
        )
        self.full_closure = full_closure
        self.years_to_close = years_to_close
        self.attending_compliance = attending_compliance  # compliance with opening
        if self.years_to_close == "all":
            self.years_to_close = list(np.arange(20))

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
                if self.full_closure:
                    return True
                elif not self._check_kid_goes_to_school(person):
                    if self.years_to_close and person.age in self.years_to_close:
                        return True
                    else:
                        if random() > self.attending_compliance:
                            return True
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
        avoid_work_probability=None,
        furlough_probability=None,
        key_probability=None,
    ):
        """
        Prevents workers with the tag ``person.lockdown_status=furlough" to go to work.
        If full_closure is True, then no one will go to work.
        """
        super().__init__(start_time, end_time, ["primary_activity", "commute"])
        self.full_closure = full_closure
        self.avoid_work_probability = avoid_work_probability
        self.furlough_probability = furlough_probability
        self.key_probability = key_probability

    def check_skips_activity(
        self, person: "Person", furlough_ratio=None, key_ratio=None, random_ratio=None
    ) -> bool:
        """
        Returns True if the activity is to be skipped, otherwise False
        """

        if (
            person.primary_activity is not None
            and person.primary_activity.group.spec == "company"
        ):

            # if companies closed skip
            if self.full_closure:
                return True

            elif person.lockdown_status == "furlough":
                if furlough_ratio is not None and self.furlough_probability is not None:
                    # if there are too few furloughed people then always furlough all
                    if furlough_ratio < self.furlough_probability:
                        return True
                    # if there are too many or correct number of furloughed people then furlough with a probability
                    elif furlough_ratio >= self.furlough_probability:
                        if random() < self.furlough_probability / furlough_ratio:
                            return True
                        # otherwise treat them as random
                        elif self.avoid_work_probability is not None:
                            if random() < self.avoid_work_probability:
                                return True
                else:
                    return True

            elif (
                person.lockdown_status == "key_worker"
                and key_ratio is not None
                and self.key_probability is not None
            ):
                # if there are too many key workers, scale them down - otherwise send all to work
                if key_ratio > self.key_probability:
                    if random() > self.key_probability / key_ratio:
                        return True

            elif (
                person.lockdown_status == "random"
                and self.avoid_work_probability is not None
            ):

                if (
                    furlough_ratio is not None
                    and self.furlough_probability is not None
                    and key_ratio is not None
                    and self.key_probability is not None
                    and random_ratio is not None
                ):
                    # if there are too few furloughed people and too few key workers
                    if (
                        furlough_ratio < self.furlough_probability
                        and key_ratio < self.key_probability
                    ):
                        if (
                            random()
                            < (self.furlough_probability - furlough_ratio)
                            / random_ratio
                        ):
                            return True
                        # correct for some random workers now being treated as furloughed
                        elif random() < (self.key_probability - key_ratio) / (
                            random_ratio - (self.furlough_probability - furlough_ratio)
                        ):
                            return False
                    # if there are too few furloughed people
                    elif furlough_ratio < self.furlough_probability:
                        if (
                            random()
                            < (self.furlough_probability - furlough_ratio)
                            / random_ratio
                        ):
                            return True
                    # if there are too few kew workers
                    elif key_ratio < self.key_probability:
                        if random() < (self.key_probability - key_ratio) / random_ratio:
                            return False

                elif (
                    furlough_ratio is not None
                    and self.furlough_probability is not None
                    and random_ratio is not None
                ):
                    # if there are too few furloughed people then randomly stop extra people from going to work
                    if furlough_ratio < self.furlough_probability:
                        if (
                            random()
                            < (self.furlough_probability - furlough_ratio)
                            / random_ratio
                        ):
                            return True

                elif (
                    key_ratio is not None
                    and self.key_probability is not None
                    and random_ratio is not None
                ):
                    # if there are too few key workers then randomly boost more people going to work and do not subject them to the random choice
                    if key_ratio < self.key_probability:
                        if random() < (self.key_probability - key_ratio) / random_ratio:
                            return False

                if random() < self.avoid_work_probability:
                    return True

        return False
