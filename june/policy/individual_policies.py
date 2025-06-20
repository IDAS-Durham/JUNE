import numpy as np
from typing import List, Optional, Union
import datetime
from random import random

from june.epidemiology.infection import SymptomTag
from june.demography.person import Person
from june.epidemiology.infection.disease_config import DiseaseConfig
from june.global_context import GlobalContext
from june.policy import Policy, PolicyCollection
from june.mpi_wrapper import mpi_size, mpi_rank
from june.records.event_recording import emit_isolation_event, emit_quarantine_event
from june.utils.distances import haversine_distance


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
                    if mpi_size == 1:
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
                if policy.check_skips_activity(person):
                    activities = policy.apply(activities=activities)
            else:
                raise ValueError("policy type not expected")
        return activities


class StayHome(IndividualPolicy):
    """
    Template for policies that will force someone to stay at home.
    """

    def __init__(self, start_time="1900-01-01", end_time="2100-01-01"):
        super().__init__(start_time=start_time, end_time=end_time)
        self.policy_subtype = "stay_home"

    def apply(self, person: Person, days_from_start: float, activities: List[str]):
        """
        Removes all activities but residence if the person has to stay at home.
        """
        if "medical_facility" in activities:
            return ("medical_facility", "residence")
        else:
            return ("residence",)

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

    def __init__(self, start_time=None, end_time=None):
        super().__init__(start_time, end_time)

    def check_stay_home_condition(self, person: Person, days_from_start: float) -> bool:
        """
        Check if the person should stay home based on severe symptoms.

        Parameters
        ----------
        person : Person
            The person to evaluate.
        days_from_start : float
            Days elapsed since the simulation started.

        Returns
        -------
        bool
            True if the person should stay home, False otherwise.
        """
        severe_symptom_tags = GlobalContext.get_disease_config().symptom_manager.severe_symptom


        # Check if the person's infection tag matches any of the severe symptom tags
        return (
            person.infection is not None
            and person.infection.tag in severe_symptom_tags
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
        vaccinated_household_compliance: float = 1.0,
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
        vaccinated_household_compliance:
            over 18s don't quarantine up to household compliance
            those fully vaccinated don't quarantine up to household compliance
        """
        super().__init__(start_time, end_time)
        self.n_days = n_days
        self.n_days_household = n_days_household
        self.compliance = compliance
        self.household_compliance = household_compliance
        self.vaccinated_household_compliance = vaccinated_household_compliance
        
        # Cache for disease config data
        self._stay_at_home_tags = None

    def _get_stay_at_home_tags(self):
        """Lazily initialize and cache the stay-at-home tags"""
        if self._stay_at_home_tags is None:
            disease_config = GlobalContext.get_disease_config()
            self._stay_at_home_tags = set(disease_config.symptom_manager.stay_at_home)
        return self._stay_at_home_tags
        
    def check_stay_home_condition(self, person: Person, days_from_start: float) -> bool:
        # Get cached stay-at-home tags
        stay_at_home_tags = self._get_stay_at_home_tags()
        
        # Get regional compliance with fast path for missing attribute
        try:
            regional_compliance = person.region.regional_compliance
        except AttributeError:
            regional_compliance = 1.0

        if person.infected:
            infection = person.infection
            time_of_symptoms_onset = infection.time_of_symptoms_onset if infection else None

            if time_of_symptoms_onset is not None:
                person.residence.group.quarantine_starting_date = time_of_symptoms_onset

                if infection.tag in stay_at_home_tags:
                    release_day = time_of_symptoms_onset + self.n_days
                    if 0 < release_day - days_from_start < self.n_days:
                        if random() < self.compliance * regional_compliance:
                            return True

        # Calculate household compliance factor once
        if person.vaccinated and not person.vaccine_trajectory or person.age < 18:
            household_compliance_factor = self.vaccinated_household_compliance * self.household_compliance * regional_compliance
        else:
            household_compliance_factor = self.household_compliance * regional_compliance

        housemates_quarantine = person.residence.group.quarantine(
            time=days_from_start,
            quarantine_days=self.n_days_household,
            household_compliance=household_compliance_factor,
        )

        
        return housemates_quarantine
    
class Quarantine4results(StayHome):
    def __init__(
        self,
        start_time: Union[str, datetime.datetime] = "1900-01-01",
        end_time: Union[str, datetime.datetime] = "2100-01-01",
        n_days: int = 1,
        compliance: float = 1.0
    ):
        super().__init__(start_time, end_time)
        self.n_days = n_days
        self.compliance = compliance
        
        # Debug flag - set to False by default
        self.debug = False

    def check_stay_home_condition(self, person, days_from_start):
        if hasattr(person,'test_and_trace') and person.test_and_trace is not None:
            if not person.hospitalised:
                if person.test_and_trace.time_of_testing is not None:
                    if days_from_start > person.test_and_trace.time_of_result and person.test_and_trace.test_result is not None: 
                        #Only people that tested positive will enter here but not really, because this happens before we apply the test result... 
                        if person.test_and_trace.emited_quarantine_end_event is None:
                            emit_quarantine_event(person, days_from_start, is_start=False)
                            person.test_and_trace.emited_quarantine_end_event = True

                            if self.debug:
                                print(f"[Rank {mpi_rank}] Person {person.id} is done Quarantining before Results (time of results: {person.test_and_trace.time_of_result}. result: {person.test_and_trace.test_result}). They now need to Self Isolate! (current time: {days_from_start})")
                            
                        return False
                    else:
                        #People waiting for results enter here
                        if person.test_and_trace.emited_quarantine_start_event is None:
                            emit_quarantine_event(person, days_from_start, is_start=True)
                            person.test_and_trace.emited_quarantine_start_event = True
                        if self.debug:
                            print(f"[Rank {mpi_rank}] Person {person.id} is Quarantining before Results! (time of results: {person.test_and_trace.time_of_result}. result: {person.test_and_trace.test_result}) current time {days_from_start}")
                        return True
            return False
            
class SelfIsolation(StayHome):
    def __init__(
            self,
            start_time: Union[str, datetime.datetime] = "1900-01-01",
            end_time: Union[str, datetime.datetime] = "2100-01-01",
            n_days: int = 10,
            compliance: float = 1.0
    ):
        super().__init__(start_time, end_time)
        self.n_days = n_days
        self.compliance = compliance
        
        # Debug flag - set to False by default
        self.debug = False

    def check_stay_home_condition(self, person, days_from_start):

        if hasattr(person, 'test_and_trace') and person.test_and_trace is not None:
            if not person.hospitalised:
                if person.test_and_trace.isolation_start_time is None: #First time comers, let's assign what they need
                    if person.test_and_trace.test_result == "Positive": #If they are positive
                        #We assign their isolation start and end times
                        person.test_and_trace.isolation_start_time = days_from_start
                        person.test_and_trace.isolation_end_time = days_from_start + self.n_days
                        emit_isolation_event(person, days_from_start, is_start=True)
                        
                        if self.debug:
                            print(f"[Rank {mpi_rank}] Person {person.id} is isolating. Isolation end time: {person.test_and_trace.isolation_end_time}. Person infected? {person.infected}. Current time: {days_from_start}")

                        return True
                    else: #If they are negative or have no results
                        return False
                else: #Coming again, we need to see if they need to stay in isolation
                    if days_from_start >= person.test_and_trace.isolation_end_time: #They finished their time. 
                        if not person.infected: #They are actually healthy
                            
                            emit_isolation_event(person, days_from_start, is_start=False)

                            if self.debug:
                                print(f"[Rank {mpi_rank}] Person {person.id} has finished their self-isolation and is healthy. Released!")
                            return False
                        if person.infected: #They are still infected
                            if self.debug:
                                print(f"[Rank {mpi_rank}] Person {person.id} has finished their self-isolation period but still have symptoms. NOT released!")
                            return True
                    if self.debug:
                        print(f"[Rank {mpi_rank}] Person {person.id} has not finished their self-isolation period yet.")
                    return True
        else:
            return False


class SchoolQuarantine(StayHome):
    def __init__(
        self,
        start_time: Union[str, datetime.datetime] = "1900-01-01",
        end_time: Union[str, datetime.datetime] = "2100-01-01",
        compliance: float = 1.0,
        n_days: int = 7,
        isolate_on: str = "symptoms",
    ):
        """
        This policy forces kids to stay at home if there is a symptomatic case of covid in their classroom.

        Parameters
        ----------
        start_time:
            date at which to start applying the policy
        end_time:
            date from which the policy won't apply
        n_days:
            days for which the person has to stay at home if they show symtpoms
        n_days_household:
            days for which the person has to stay at home if someone in their household
            shows symptoms
        compliance:
            percentage of symptomatic people that will adhere to the quarantine policy
        household_compliance:
            percentage of people that will adhere to the hoseuhold quarantine policy
        """
        super().__init__(start_time, end_time)
        self.compliance = compliance
        self.n_days = n_days
        self.isolate_on = isolate_on

    def check_stay_home_condition(self, person: Person, days_from_start):
        try:
            if (
                not person.primary_activity.group.spec == "school"
                or person.primary_activity.group.external
            ):
                return False
        except Exception:
            return False
        try:
            regional_compliance = person.region.regional_compliance
        except Exception:
            regional_compliance = 1
        compliance = self.compliance * regional_compliance
        if person.infected:
            # infected people set quarantine date to the school.
            # there is no problem in order as this will activate
            # days before it is actually applied (during incubation time).
            if self.isolate_on == "infection":
                time_start_quarantine = person.infection.start_time
            else:
                if person.infection.time_of_symptoms_onset:
                    time_start_quarantine = (
                        person.infection.start_time
                        + person.infection.time_of_symptoms_onset
                    )
                else:
                    time_start_quarantine = None
            if time_start_quarantine is not None:
                if (
                    time_start_quarantine
                    < person.primary_activity.quarantine_starting_date
                ):
                    # If the agent will show symptoms earlier than the quarantine time, update it.
                    person.primary_activity.quarantine_starting_date = (
                        time_start_quarantine
                    )
                if (
                    days_from_start - person.primary_activity.quarantine_starting_date
                ) > self.n_days:
                    # If it's been more than n_days since last quarantine
                    person.primary_activity.quarantine_starting_date = (
                        time_start_quarantine
                    )
        if (
            0
            < (days_from_start - person.primary_activity.quarantine_starting_date)
            < self.n_days
        ):
            return random() < compliance
        return False


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
        try:
            regional_compliance = person.region.regional_compliance
        except Exception:
            regional_compliance = 1
        if person.age >= self.min_age:
            if (
                self.compliance is None
                or random() < self.compliance * regional_compliance
            ):
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
            start_time, end_time, activities_to_remove=("primary_activity")
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
    def __init__(self, start_time: str, end_time: str):
        super().__init__(
            start_time, end_time, activities_to_remove=("primary_activity")
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


class CloseCompaniesLockdownTiers(SkipActivity):
    TIERS = set([3, 4])

    def __init__(self, start_time: str, end_time: str):
        super().__init__(start_time, end_time, ("primary_activity", "commute"))

    def check_skips_activity(self, person: "Person") -> bool:
        """
        Returns True if the activity is to be skipped, otherwise False
        """
        if (
            person.primary_activity is not None
            and person.primary_activity.group.spec == "company"
        ):
            # import pdb; pdb.set_trace()
            if person.lockdown_status == "random":
                # stop people going to work in Tier 3 or 4 regions
                # if they don't work in the same region
                # and if their region is not in Tier 3 or 4
                # subject to regional compliance
                try:
                    if (
                        person.work_super_area != person.area.super_area
                        and person.work_super_area.region.policy["lockdown_tier"]
                        in CloseCompaniesLockdownTiers.TIERS
                        and person.region.policy["lockdown_tier"]
                        not in CloseCompaniesLockdownTiers.TIERS
                    ):
                        try:
                            return random() < person.region.regional_compliance
                        except Exception:
                            return True
                except AttributeError:
                    pass

                # stop people going to work who are living in a Tier 3 or 4 region unless they work
                # in that same region
                # subject to regional compliance
                try:
                    if (
                        person.work_super_area != person.area.super_area
                        and person.region.policy["lockdown_tier"]
                        in CloseCompaniesLockdownTiers.TIERS
                    ):
                        try:
                            return random() < person.region.regional_compliance
                        except Exception:
                            return True
                except AttributeError:
                    pass
        return False


class CloseCompanies(SkipActivity):
    furlough_ratio = None
    key_ratio = None
    random_ratio = None

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
        super().__init__(start_time, end_time, ("primary_activity", "commute"))
        self.full_closure = full_closure
        self.avoid_work_probability = avoid_work_probability
        self.furlough_probability = furlough_probability
        self.key_probability = key_probability

    @classmethod
    def initialize(cls, world, date, record):
        furlough_ratio = 0
        key_ratio = 0
        random_ratio = 0
        for person in world.people:
            if person.lockdown_status == "furlough":
                furlough_ratio += 1
            elif person.lockdown_status == "key_worker":
                key_ratio += 1
            elif person.lockdown_status == "random":
                random_ratio += 1
        if furlough_ratio != 0 and key_ratio != 0 and random_ratio != 0:
            furlough_ratio /= furlough_ratio + key_ratio + random_ratio
            key_ratio /= furlough_ratio + key_ratio + random_ratio
            random_ratio /= furlough_ratio + key_ratio + random_ratio
        else:
            furlough_ratio = None
            key_ratio = None
            random_ratio = None
        cls.furlough_ratio = furlough_ratio
        cls.key_ratio = key_ratio
        cls.random_ratio = random_ratio

    def check_skips_activity(self, person: "Person") -> bool:
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
                if (
                    self.furlough_ratio is not None
                    and self.furlough_probability is not None
                ):
                    # if there are too few furloughed people then always furlough all
                    if self.furlough_ratio < self.furlough_probability:
                        return True
                    # if there are too many or correct number of furloughed people then furlough with a probability
                    elif self.furlough_ratio >= self.furlough_probability:
                        if random() < self.furlough_probability / self.furlough_ratio:
                            return True
                        # otherwise treat them as random
                        elif self.avoid_work_probability is not None:
                            if random() < self.avoid_work_probability:
                                return True
                else:
                    return True

            elif (
                person.lockdown_status == "key_worker"
                and self.key_ratio is not None
                and self.key_probability is not None
            ):
                # if there are too many key workers, scale them down - otherwise send all to work
                if self.key_ratio > self.key_probability:
                    if random() > self.key_probability / self.key_ratio:
                        return True

            elif (
                person.lockdown_status == "random"
                and self.avoid_work_probability is not None
            ):

                if (
                    self.furlough_ratio is not None
                    and self.furlough_probability is not None
                    and self.key_ratio is not None
                    and self.key_probability is not None
                    and self.random_ratio is not None
                ):
                    # if there are too few furloughed people and too few key workers
                    if (
                        self.furlough_ratio < self.furlough_probability
                        and self.key_ratio < self.key_probability
                    ):
                        if (
                            random()
                            < (self.furlough_probability - self.furlough_ratio)
                            / self.random_ratio
                        ):
                            return True
                        # correct for some random workers now being treated as furloughed
                        elif random() < (self.key_probability - self.key_ratio) / (
                            self.random_ratio
                            - (self.furlough_probability - self.furlough_ratio)
                        ):
                            return False
                    # if there are too few furloughed people
                    elif self.furlough_ratio < self.furlough_probability:
                        if (
                            random()
                            < (self.furlough_probability - self.furlough_ratio)
                            / self.random_ratio
                        ):
                            return True
                    # if there are too few kew workers
                    elif self.key_ratio < self.key_probability:
                        if (
                            random()
                            < (self.key_probability - self.key_ratio)
                            / self.random_ratio
                        ):
                            return False

                elif (
                    self.furlough_ratio is not None
                    and self.furlough_probability is not None
                    and self.random_ratio is not None
                ):
                    # if there are too few furloughed people then randomly stop extra people from going to work
                    if self.furlough_ratio < self.furlough_probability:
                        if (
                            random()
                            < (self.furlough_probability - self.furlough_ratio)
                            / self.random_ratio
                        ):
                            return True

                elif (
                    self.key_ratio is not None
                    and self.key_probability is not None
                    and self.random_ratio is not None
                ):
                    # if there are too few key workers then randomly boost more people going to work and do not subject them to the random choice
                    if self.key_ratio < self.key_probability:
                        if (
                            random()
                            < (self.key_probability - self.key_ratio)
                            / self.random_ratio
                        ):
                            return False

                if random() < self.avoid_work_probability:
                    return True

        return False


class LimitLongCommute(SkipActivity):
    """
    Limits long distance commuting from a certain distance.
    If the person has its workplace further than a certain threshold,
    then their probability of going to work every day decreases.
    """

    long_distance_commuter_ids = set()
    apply_from_distance = 150

    def __init__(
        self,
        start_time: str = "1000-01-01",
        end_time: str = "9999-12-31",
        apply_from_distance: float = 150,
        going_to_work_probability: float = 0.2,
    ):
        super().__init__(
            start_time, end_time, activities_to_remove=("primary_activity", "commute")
        )
        self.going_to_work_probability = going_to_work_probability
        self.__class__.apply_from_distance = apply_from_distance
        self.__class__.long_distance_commuter_ids = set()

    def initialize(self, world, date, record):
        return self.get_long_commuters(world.people)

    @classmethod
    def get_long_commuters(cls, people):
        for person in people:
            if cls._does_long_commute(person):
                cls.long_distance_commuter_ids.add(person.id)

    @classmethod
    def _does_long_commute(cls, person: Person):
        if person.work_super_area is None:
            return False
        distance_to_work = haversine_distance(
            person.area.coordinates, person.work_super_area.coordinates
        )
        if distance_to_work > cls.apply_from_distance:
            return True
        return False

    def check_skips_activity(self, person: Person):
        if person.id not in self.long_distance_commuter_ids:
            return False
        else:
            if random() < self.going_to_work_probability:
                return True
            else:
                return False
