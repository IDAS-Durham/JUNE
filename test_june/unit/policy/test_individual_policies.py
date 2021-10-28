from datetime import datetime

import numpy as np
import pytest

from june.demography import Person
from june.geography import Area, SuperArea
from june.geography.geography import Region
from june.groups import School, Household
from june.epidemiology.infection import SymptomTag
from june.policy import (
    SevereSymptomsStayHome,
    CloseSchools,
    CloseCompanies,
    CloseUniversities,
    Quarantine,
    Shielding,
    Policies,
    Hospitalisation,
    LimitLongCommute,
    SchoolQuarantine,
)
from june.policy.individual_policies import CloseCompaniesLockdownTiers
from june.utils.distances import haversine_distance


def infect_person(person, selector, symptom_tag="mild"):
    selector.infect_person_at_time(person, 0.0)
    person.infection.symptoms.tag = getattr(SymptomTag, symptom_tag)
    if symptom_tag != "asymptomatic":
        person.infection.symptoms.time_of_symptoms_onset = 5.3
        person.residence.group.quarantine_starting_date = 5.3
    else:
        person.infection.symptoms.time_of_symptoms_onset = None


class TestSevereSymptomsStayHome:
    def test__policy_adults(self, setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        permanent_policy = SevereSymptomsStayHome()
        policies = Policies([permanent_policy])
        sim.activity_manager.policies = policies
        sim.epidemiology.set_medical_care(world, sim.activity_manager)
        sim.clear_world()
        sim.activity_manager.move_people_to_active_subgroups(
            ("primary_activity", "residence"),
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        infect_person(worker, selector, "severe")
        sim.epidemiology.update_health_status(world, 0.0, 0.0)
        sim.activity_manager.move_people_to_active_subgroups(
            ("primary_activity", "residence"),
        )
        assert worker in worker.residence.people
        assert pupil in pupil.primary_activity.people
        worker.infection = None
        sim.clear_world()

    def test__policy_adults_still_go_to_hospital(self, setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        permanent_policy = SevereSymptomsStayHome()
        hospitalisation = Hospitalisation()
        policies = Policies([permanent_policy, hospitalisation])
        sim.activity_manager.policies = policies
        sim.epidemiology.set_medical_care(world, sim.activity_manager)
        sim.clear_world()
        sim.activity_manager.move_people_to_active_subgroups(
            ["medical_facility", "primary_activity", "residence"],
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        infect_person(worker, selector, "hospitalised")
        sim.epidemiology.update_health_status(world, 0.0, 0.0)
        sim.activity_manager.move_people_to_active_subgroups(
            ["medical_facility", "primary_activity", "residence"],
        )
        assert worker in worker.medical_facility.people
        assert pupil in pupil.primary_activity.people
        worker.infection = None
        sim.clear_world()

    def test__default_policy_kids(self, selector, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        permanent_policy = SevereSymptomsStayHome()
        policies = Policies([permanent_policy])
        sim.activity_manager.policies = policies
        sim.epidemiology.set_medical_care(world, sim.activity_manager)
        sim.clear_world()
        sim.activity_manager.move_people_to_active_subgroups(
            ["primary_activity", "residence"],
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        assert student in student.primary_activity.people
        sim.clear_world()
        infect_person(pupil, selector, "severe")
        sim.epidemiology.update_health_status(world, 0.0, 0.0)
        assert pupil.infection.tag == SymptomTag.severe
        sim.activity_manager.move_people_to_active_subgroups(
            ["primary_activity", "residence"],
        )
        assert pupil in pupil.residence.people
        has_guardian = False
        for person in [worker, student]:
            if person in person.residence.people:
                has_guardian = True
                break
        assert has_guardian
        sim.clear_world()


class TestClosure:
    def test__close_schools(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        school_closure = CloseSchools(
            start_time="2020-1-1",
            end_time="2020-10-1",
            years_to_close=[6],
        )
        policies = Policies([school_closure])
        sim.activity_manager.policies = policies
        sim.epidemiology.set_medical_care(world, sim.activity_manager)

        # non key worker
        worker.lockdown_status = "furlough"
        sim.clear_world()
        activities = ["primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_before_policy
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        assert policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=0,
        ) == [
            "residence",
        ]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert pupil in pupil.residence.people
        assert worker in worker.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_after_policy
        )
        assert policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=0,
        ) == [
            "primary_activity",
            "residence",
        ]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

        # key worker
        worker.lockdown_status = "key_worker"
        student.lockdown_status = "key_worker"
        sim.clear_world()
        activities = ["primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_before_policy
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        assert policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=0,
        ) == [
            "primary_activity",
            "residence",
        ]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_after_policy
        )
        assert policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=0,
        ) == [
            "primary_activity",
            "residence",
        ]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__reopen_schools(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        school_closure = CloseSchools(
            start_time="2020-1-1",
            end_time="2020-10-1",
            attending_compliance=0.5,
        )
        policies = Policies([school_closure])
        sim.activity_manager.policies = policies

        # non key worker
        worker.lockdown_status = "furlough"
        sim.clear_world()
        activities = ["primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_before_policy
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )

        # Move the pupil 500 times for five days
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=pupil,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(2.5, rel=0.1)
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert worker in worker.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_after_policy
        )
        assert policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=0,
        ) == [
            "primary_activity",
            "residence",
        ]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

        # key worker
        worker.lockdown_status = "key_worker"
        student.lockdown_status = "key_worker"
        sim.clear_world()
        activities = ["primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_before_policy
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        # Move the pupil 500 times for five days
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=pupil,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(5.0, rel=0.1)
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_after_policy
        )
        assert policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=0,
        ) == [
            "primary_activity",
            "residence",
        ]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__close_universities(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        university_closure = CloseUniversities(
            start_time="2020-1-1",
            end_time="2020-10-1",
        )
        policies = Policies([university_closure])
        sim.activity_manager.policies = policies
        sim.clear_world()
        activities = ["primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_before_policy
        )
        assert student in student.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        assert policies.individual_policies.apply(
            active_individual_policies,
            person=student,
            activities=activities,
            days_from_start=0,
        ) == [
            "residence",
        ]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert student in student.residence.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_after_policy
        )
        assert (
            policies.individual_policies.apply(
                active_individual_policies,
                person=student,
                activities=activities,
                days_from_start=0,
            )
            == ["primary_activity", "residence"]
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert student in student.primary_activity.people
        sim.clear_world()

    def test__close_companies_lockdown_tiers(self, setup_policy_world):
        live_region = Region()
        work_region = Region()
        world, pupil, student, worker, sim = setup_policy_world
        worker.lockdown_status = "random"
        live_area = Area()
        live_super_area = SuperArea(name="live_super_area", coordinates=[0, 3], region=live_region, areas=[live_area])
        live_area.super_area = live_super_area
        live_region.super_areas = [live_super_area]
        work_super_area = SuperArea(name="work_super_area", coordinates=[0, 0], region=work_region)
        work_region.super_areas = [work_super_area]

        live_area.add(worker)
        worker.area = live_area
        work_super_area.add_worker(worker)
        company_closure_lockdown_tiers = CloseCompaniesLockdownTiers(start_time="2020-1-1", end_time="2020-10-1")

        # Make sure apply removes correct activities
        activities_before = ["commute", "primary_activity"]
        assert company_closure_lockdown_tiers.apply(activities_before) == []

        # Work in tier 3 or 4 and live in a tier 1 or 2: skip activity
        live_tiers = [1, 2]
        work_tiers = [3, 4]
        for live_tier, work_tier in zip(live_tiers, work_tiers):
            worker.work_super_area.region.policy['lockdown_tier'] = work_tier
            worker.region.policy['lockdown_tier'] = live_tier
            worker.region.policy['regional_compliance'] = 1  # Want them to comply this time

            assert company_closure_lockdown_tiers.check_skips_activity(worker) is True

            worker.region.policy['regional_compliance'] = 0  # Want them to not comply this time
            assert company_closure_lockdown_tiers.check_skips_activity(worker) is False


        # Live in a tier 3 or 4 and work in another region: skip activity
        live_tiers = [3, 4, 3, 4]
        work_tiers = [1, 2, 3, 4]
        for live_tier, work_tier in zip(live_tiers, work_tiers):
            worker.work_super_area.region.policy['lockdown_tier'] = work_tier
            worker.region.policy['lockdown_tier'] = live_tier
            worker.region.policy['regional_compliance'] = 1  # Want them to comply this time

            assert company_closure_lockdown_tiers.check_skips_activity(worker) is True

            worker.region.policy['regional_compliance'] = 0  # Want them to not comply this time
            assert company_closure_lockdown_tiers.check_skips_activity(worker) is False

        # Live and work in a tier 1 or 2: Never skip
        live_tiers = [1, 2, 1, 2]
        work_tiers = [1, 1, 2, 2]
        for live_tier, work_tier in zip(live_tiers, work_tiers):
            worker.work_super_area.region.policy['lockdown_tier'] = work_tier
            worker.region.policy['lockdown_tier'] = live_tier
            worker.region.policy['regional_compliance'] = 1  # Want them to comply this time

            assert company_closure_lockdown_tiers.check_skips_activity(worker) is False

        # Live in a tier 3 or 4 AND work in same region: Do not skip as allowed to go to work
        live_tiers = [3, 4, 3, 4]
        work_tiers = [3, 4, 4, 4]
        live_super_area.add_worker(worker)
        for live_tier, work_tier in zip(live_tiers, work_tiers):
            worker.work_super_area.region.policy['lockdown_tier'] = work_tier
            worker.region.policy['lockdown_tier'] = live_tier
            worker.region.policy['regional_compliance'] = 1  # Want them to comply this time

            assert company_closure_lockdown_tiers.check_skips_activity(worker) is False

    def test__close_companies(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        company_closure = CloseCompanies(start_time="2020-1-1", end_time="2020-10-1")
        policies = Policies([company_closure])
        sim.activity_manager.policies = policies
        sim.clear_world()
        activities = ["commute", "primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        worker.lockdown_status = "furlough"
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_before_policy
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        assert (
            policies.individual_policies.apply(
                active_individual_policies,
                person=worker,
                activities=activities,
                days_from_start=0,
            )
            == ["residence"]
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert worker in worker.residence.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_after_policy
        )
        assert (
            policies.individual_policies.apply(
                active_individual_policies,
                person=worker,
                activities=activities,
                days_from_start=0,
            )
            == ["commute", "primary_activity", "residence"]
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

        # no furlough
        sim.clear_world()
        activities = ["commute", "primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        worker.lockdown_status = "key_worker"
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_before_policy
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        assert (
            policies.individual_policies.apply(
                active_individual_policies,
                person=worker,
                activities=activities,
                days_from_start=0,
            )
            == ["commute", "primary_activity", "residence"]
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_after_policy
        )
        assert (
            policies.individual_policies.apply(
                active_individual_policies,
                person=worker,
                activities=activities,
                days_from_start=0,
            )
            == ["commute", "primary_activity", "residence"]
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__close_companies_frequency_of_randoms(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        company_closure = CloseCompanies(
            start_time="2020-1-1", end_time="2020-10-1", avoid_work_probability=0.2
        )
        policies = Policies([company_closure])
        sim.activity_manager.policies = policies
        sim.clear_world()
        activities = ["commute", "primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        worker.lockdown_status = "random"
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_before_policy
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        # Move the person 1_0000 times for five days
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(4.0, rel=0.1)
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(10):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 0.5
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(4.0, rel=0.1)

        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_after_policy
        )
        assert policies.individual_policies.apply(
            active_individual_policies,
            person=worker,
            activities=activities,
            days_from_start=0,
        ) == [
            "commute",
            "primary_activity",
            "residence",
        ]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__close_companies_frequency_of_furlough_ratio(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        company_closure = CloseCompanies(
            start_time="2020-1-1",
            end_time="2020-10-1",
            furlough_probability=0.2,
            avoid_work_probability=0.2,
        )
        policies = Policies([company_closure])
        sim.activity_manager.policies = policies
        sim.clear_world()
        activities = ["commute", "primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        worker.lockdown_status = "furlough"
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_before_policy
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        # Move the person 1_0000 times for five days
        company_closure.furlough_ratio = 0.0
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(0.0, rel=0.1)
        company_closure.furlough_ratio = 0.1
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(0.0, rel=0.1)
        n_days_in_week = []
        company_closure.furlough_ratio = 0.4
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(2.0, rel=0.1)

        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_after_policy
        )
        assert policies.individual_policies.apply(
            active_individual_policies,
            person=worker,
            activities=activities,
            days_from_start=0,
        ) == [
            "commute",
            "primary_activity",
            "residence",
        ]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__close_companies_frequency_of_key_ratio(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        company_closure = CloseCompanies(
            start_time="2020-1-1", end_time="2020-10-1", key_probability=0.2
        )
        policies = Policies([company_closure])
        sim.activity_manager.policies = policies
        sim.clear_world()
        activities = ["commute", "primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        worker.lockdown_status = "key_worker"
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_before_policy
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        # Move the person 1_0000 times for five days

        # Testing key_ratio and key_worker feature in random_ratio
        company_closure.key_ratio = 0.0
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(5.0, rel=0.1)
        company_closure.key_ratio = 0.1
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(5.0, rel=0.1)
        company_closure.key_ratio = 0.4
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(2.5, rel=0.1)

        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_after_policy
        )
        assert policies.individual_policies.apply(
            active_individual_policies,
            person=worker,
            activities=activities,
            days_from_start=0,
        ) == [
            "commute",
            "primary_activity",
            "residence",
        ]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__close_companies_frequency_of_random_ratio(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        company_closure = CloseCompanies(
            start_time="2020-1-1",
            end_time="2020-10-1",
            avoid_work_probability=0.2,
            key_probability=0.2,
            furlough_probability=0.2,
        )
        policies = Policies([company_closure])
        sim.activity_manager.policies = policies
        sim.clear_world()
        activities = ["commute", "primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        worker.lockdown_status = "random"
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_before_policy
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        # Move the person 1_0000 times for five days

        # Testing key_ratio feature in random_ratio
        company_closure.random_ratio = 1.0
        company_closure.key_ratio = 0.0
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(4.2, rel=0.1)
        n_days_in_week = []
        company_closure.random_ratio = 1.0
        company_closure.key_ratio = 0.1
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(4.1, rel=0.1)
        company_closure.random_ratio = 1.0
        company_closure.key_ratio = 0.2
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(4.0, rel=0.1)
        company_closure.key_ratio = 0.0
        company_closure.random_ratio = 1.0
        company_closure.furlough_ratio = 0.0
        # Testing furlough_ratio feature in random_ratio
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(3.2, rel=0.1)
        n_days_in_week = []
        company_closure.random_ratio = 1.0
        company_closure.furlough_ratio = 0.1
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(3.6, rel=0.1)
        n_days_in_week = []
        company_closure.random_ratio = 1.0
        company_closure.furlough_ratio = 0.3
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(4.0, rel=0.1)

        # Testing furlough_ratio and key_ratio mixing feature in random_ratio
        n_days_in_week = []
        company_closure.random_ratio = 1.0
        company_closure.furlough_ratio = 0.0
        company_closure.key_ratio = 0.0
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(3.4, rel=0.1)
        n_days_in_week = []
        company_closure.random_ratio = 1.0
        company_closure.key_ratio = 0.0
        company_closure.furlough_ratio = 0.1
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(3.8, rel=0.1)
        n_days_in_week = []
        company_closure.random_ratio = 1.0
        company_closure.furlough_ratio = 0.1
        company_closure.key_ratio = 0.1
        for i in range(1000):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(3.7, rel=0.1)
        n_days_in_week = []
        company_closure.random_ratio = 1.0
        company_closure.furlough_ratio = 0.3
        company_closure.key_ratio = 0.3
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in policies.individual_policies.apply(
                    active_individual_policies,
                    person=worker,
                    activities=activities,
                    days_from_start=0,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(4.0, rel=0.1)

        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_after_policy
        )
        assert policies.individual_policies.apply(
            active_individual_policies,
            person=worker,
            activities=activities,
            days_from_start=0,
        ) == [
            "commute",
            "primary_activity",
            "residence",
        ]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__close_companies_full_closure(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        company_closure = CloseCompanies(
            start_time="2020-1-1",
            end_time="2020-10-1",
            full_closure=True,
        )
        policies = Policies([company_closure])
        sim.activity_manager.policies = policies
        worker.lockdown_status = "key_worker"
        activities = ["commute", "primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        assert (
            policies.individual_policies.apply(
                active_individual_policies,
                person=worker,
                activities=activities,
                days_from_start=0,
            )
            == ["residence"]
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert worker in worker.residence.people
        sim.clear_world()


class TestShielding:
    def test__old_people_shield(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        shielding = Shielding(start_time="2020-1-1", end_time="2020-10-1", min_age=30)
        policies = Policies([shielding])
        sim.activity_manager.policies = policies
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        assert "primary_activity" not in policies.individual_policies.apply(
            active_individual_policies,
            person=worker,
            activities=activities,
            days_from_start=0,
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert worker in worker.residence.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()

    def test__old_people_shield_with_compliance(self, setup_policy_world):
        world, pupil, student, worker, _ = setup_policy_world
        shielding = Shielding(
            start_time="2020-1-1", end_time="2020-10-1", min_age=30, compliance=0.6
        )
        policies = Policies([shielding])
        activities = ["primary_activity", "residence"]
        time_during_policy = datetime(2020, 2, 1)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        compliant_days = 0
        for i in range(100):
            if "primary_activity" not in policies.individual_policies.apply(
                active_individual_policies,
                person=worker,
                activities=activities,
                days_from_start=0,
            ):
                compliant_days += 1

        assert compliant_days / 100 == pytest.approx(shielding.compliance, abs=0.1)


class TestQuarantine:
    def test__symptomatic_stays_for_one_week(self, setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        quarantine = Quarantine(
            start_time="2020-1-1",
            end_time="2020-1-30",
            n_days=7,
            n_days_household=14,
        )
        policies = Policies([quarantine])
        sim.activity_manager.policies = policies
        infect_person(worker, selector, "mild")
        sim.epidemiology.update_health_status(world, 0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        assert "primary_activity" not in policies.individual_policies.apply(
            active_individual_policies,
            person=worker,
            activities=activities,
            days_from_start=6,
        )
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=worker,
            activities=activities,
            days_from_start=20,
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy, 6.0
        )
        assert worker in worker.residence.people
        sim.clear_world()
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy, 20
        )
        assert worker in worker.primary_activity.people
        worker.infection = None
        sim.clear_world()

    def test__asymptomatic_is_free(self, setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        quarantine = Quarantine(
            start_time="2020-1-1",
            end_time="2020-1-30",
            n_days=7,
            n_days_household=14,
        )
        policies = Policies([quarantine])
        sim.activity_manager.policies = policies
        infect_person(worker, selector, "asymptomatic")
        sim.epidemiology.update_health_status(world, 0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=worker,
            activities=activities,
            days_from_start=6.0,
        )
        worker.infection = None
        sim.clear_world()

    def test__housemates_stay_for_two_weeks(self, setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        quarantine = Quarantine(
            start_time="2020-1-1",
            end_time="2020-1-30",
            n_days=7,
            n_days_household=14,
        )
        policies = Policies([quarantine])
        sim.activity_manager.policies = policies
        infect_person(worker, selector, "mild")
        sim.epidemiology.update_health_status(world, 0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        # before symptoms onset
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        assert "primary_activity" not in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=8.0,
        )
        # after symptoms onset
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy, 8.0
        )
        assert pupil in pupil.residence.people
        # more thatn two weeks after symptoms onset
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=25,
        )
        worker.infection = None
        sim.clear_world()
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy, 25
        )
        assert pupil in pupil.primary_activity.people
        sim.clear_world()

    def test__housemates_of_asymptomatic_are_free(self, setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        quarantine = Quarantine(
            start_time="2020-1-1",
            end_time="2020-1-30",
            n_days=7,
            n_days_household=14,
        )
        policies = Policies([quarantine])
        sim.activity_manager.policies = policies
        infect_person(worker, selector, "asymptomatic")
        sim.epidemiology.update_health_status(world, 0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        # after symptoms onset
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=8.0,
        )
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=25.0,
        )
        worker.infection = None
        sim.clear_world()

    def test__quarantine_zero_complacency(self, setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        quarantine = Quarantine(
            start_time="2020-1-1",
            end_time="2020-1-30",
            n_days=7,
            n_days_household=14,
            household_compliance=0.0,
        )
        policies = Policies([quarantine])
        sim.activity_manager.policies = policies
        infect_person(worker, selector, "mild")
        sim.epidemiology.update_health_status(world, 0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        # before symptoms onset
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=4.0,
        )
        # after symptoms onset
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=8.0,
        )
        # more thatn two weeks after symptoms onset
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=25,
        )
        worker.infection = None
        sim.clear_world()

    def test__quarantine_zero_complacency_regional(self, setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        world.regions[0].regional_compliance = 0
        quarantine = Quarantine(
            start_time="2020-1-1",
            end_time="2020-1-30",
            n_days=7,
            n_days_household=14,
        )
        policies = Policies([quarantine])
        sim.activity_manager.policies = policies
        infect_person(worker, selector, "mild")
        sim.epidemiology.update_health_status(world, 0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        # before symptoms onset
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=4.0,
        )
        # after symptoms onset
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=8.0,
        )
        # more thatn two weeks after symptoms onset
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=25,
        )
        worker.infection = None
        sim.clear_world()

    def test__quarantine_vaccinated_are_free(self, setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        quarantine = Quarantine(
            start_time="2020-1-1",
            end_time="2020-1-30",
            n_days=7,
            n_days_household=14,
            household_compliance=1.0,
            vaccinated_household_compliance=0.0,
        )
        pupil.age = 19  # such that they aren't caught in the under 18 rule
        pupil.vaccinated = True
        policies = Policies([quarantine])
        sim.activity_manager.policies = policies
        infect_person(worker, selector, "mild")
        sim.epidemiology.update_health_status(world, 0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        # before symptoms onset
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=4.0,
        )
        # after symptoms onset
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=8.0,
        )
        # more thatn two weeks after symptoms onset
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=25,
        )
        worker.infection = None
        sim.clear_world()

    def test__quarantine_children_are_free(self, setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        quarantine = Quarantine(
            start_time="2020-1-1",
            end_time="2020-1-30",
            n_days=7,
            n_days_household=14,
            household_compliance=1.0,
            vaccinated_household_compliance=0.0,
        )
        pupil.age = 17
        policies = Policies([quarantine])
        sim.activity_manager.policies = policies
        infect_person(worker, selector, "mild")
        sim.epidemiology.update_health_status(world, 0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        active_individual_policies = policies.individual_policies.get_active(
            date=time_during_policy
        )
        # before symptoms onset
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=4.0,
        )
        # after symptoms onset
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=8.0,
        )
        # more thatn two weeks after symptoms onset
        assert "primary_activity" in policies.individual_policies.apply(
            active_individual_policies,
            person=pupil,
            activities=activities,
            days_from_start=25,
        )
        worker.infection = None
        sim.clear_world()


def test__kid_at_home_is_supervised(setup_policy_world, selector):
    world, pupil, student, worker, sim = setup_policy_world
    policies = Policies([SevereSymptomsStayHome()])
    sim.activity_manager.policies = policies
    assert pupil.primary_activity is not None
    infect_person(pupil, selector, "severe")
    assert pupil.infection.tag == SymptomTag.severe
    sim.activity_manager.move_people_to_active_subgroups(
        ["primary_activity", "residence"]
    )
    assert pupil in pupil.residence.people
    guardians_at_home = [
        person for person in pupil.residence.group.people if person.age >= 18
    ]
    assert len(guardians_at_home) != 0
    sim.clear_world()


class TestLimitLongCommute:
    def test__haversine_distance(self):
        area = Area(coordinates=[0, 1])
        super_area = SuperArea(coordinates=[0, 0])
        distance = haversine_distance(area.coordinates, super_area.coordinates)
        assert 100 < distance < 150

    def test__distance_policy_check(self):
        worker = Person.from_attributes()
        area = Area(coordinates=[0, 1])
        super_area = SuperArea(coordinates=[0, 0])
        super_area.add_worker(worker)
        area.add(worker)
        limit_long_commute = LimitLongCommute(
            apply_from_distance=150, going_to_work_probability=0.2
        )
        ret = limit_long_commute._does_long_commute(worker)
        assert ret is False

    def test__probability_of_going_to_work(self):
        worker = Person.from_attributes()
        area = Area(coordinates=[0, 3])
        super_area = SuperArea(coordinates=[0, 0])
        area.add(worker)
        super_area.add_worker(worker)
        limit_long_commute = LimitLongCommute(
            apply_from_distance=150, going_to_work_probability=0.2
        )
        assert set(limit_long_commute.activities_to_remove) == set(
            [
                "commute",
                "primary_activity",
            ]
        )
        limit_long_commute.get_long_commuters([worker])
        skips = 0
        n = 5000
        for _ in range(n):
            ret = limit_long_commute.check_skips_activity(worker)
            if ret:
                skips += 1
        assert np.isclose(skips, 0.2 * n, rtol=0.1)


class TestSchoolQuarantine:
    def test__school_quarantine(self, selector):
        kids = []
        school = School()
        household = Household()
        for i in range(10):
            for _ in range(100):
                person = Person.from_attributes(age=i)
                school.add(person)
                household.add(person)
                kids.append(person)
        school_quarantine = SchoolQuarantine(
            start_time="2020-1-1", end_time="2020-1-30", compliance=0.7, n_days=7
        )
        infected = kids[0]
        infect_person(infected, selector=selector, symptom_tag="mild")
        time = 0
        checks = [False, False, False]
        while True:
            if time > 7 + infected.infection.time_of_symptoms_onset:
                checks[0] = True
                for person in kids:
                    stays_home = school_quarantine.check_stay_home_condition(
                        person=person, days_from_start=time
                    )
                    assert stays_home is False
                break
            if time < infected.infection.time_of_symptoms_onset:
                checks[1] = True
                for person in kids:
                    stays_home = school_quarantine.check_stay_home_condition(
                        person=person, days_from_start=time
                    )
                    assert stays_home is False
                time += 1
            else:
                checks[2] = True
                quarantined = 0
                total = 0
                for person in kids:
                    stays_home = school_quarantine.check_stay_home_condition(
                        person=person, days_from_start=time
                    )
                    if person.primary_activity == infected.primary_activity:
                        total += 1
                        if stays_home:
                            quarantined += 1
                    else:
                        assert stays_home is False
                assert np.isclose(quarantined / total, 0.7, rtol=0.15)
                time += 1
        assert min(checks) is True
