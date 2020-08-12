import copy
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from june import paths
from june.demography import Person, Population
from june.demography.geography import Geography
from june.groups import Hospital, School, Company, Household, University
from june.groups import (
    Hospitals,
    Schools,
    Companies,
    Households,
    Universities,
    Cemeteries,
)
from june.groups.leisure import leisure, Cinemas, Pubs, Cinema, Pub
from june.infection import SymptomTag
from june.infection.infection import InfectionSelector
from june.policy import (
    Policy,
    SevereSymptomsStayHome,
    CloseSchools,
    CloseCompanies,
    CloseUniversities,
    Quarantine,
    Shielding,
    Policies,
    IndividualPolicies,
    Hospitalisation
)
from june.simulator import Simulator
from june.world import World

def infect_person(person, selector, symptom_tag="mild"):
    selector.infect_person_at_time(person, 0.0)
    person.health_information.infection.symptoms.tag = getattr(SymptomTag, symptom_tag)
    person.health_information.time_of_symptoms_onset = 5.3
    if symptom_tag != "asymptomatic":
        person.residence.group.quarantine_starting_date = 5.3

class TestSevereSymptomsStayHome:
    def test__policy_adults(self,  setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        permanent_policy = SevereSymptomsStayHome()
        policies = Policies([permanent_policy])
        sim.activity_manager.policies = policies
        sim.clear_world()
        sim.activity_manager.move_people_to_active_subgroups(
            ["primary_activity", "residence"],
        )
        date = datetime(2019, 2, 1)
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        infect_person(worker, selector, "severe")
        sim.update_health_status(0.0, 0.0)
        sim.activity_manager.move_people_to_active_subgroups(
            ["primary_activity", "residence"],
        )
        assert worker in worker.residence.people
        assert pupil in pupil.primary_activity.people
        worker.health_information = None
        sim.clear_world()

    def test__policy_adults_still_go_to_hospital(
        self, setup_policy_world, selector
    ):
        world, pupil, student, worker, sim = setup_policy_world
        permanent_policy = SevereSymptomsStayHome()
        hospitalisation = Hospitalisation()
        policies = Policies([permanent_policy, hospitalisation])
        sim.activity_manager.policies = policies
        sim.clear_world()
        sim.activity_manager.move_people_to_active_subgroups(
            ["medical_facility", "primary_activity", "residence"],
        )
        date = datetime(2019, 2, 1)
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        infect_person(worker, selector, "hospitalised")
        sim.update_health_status(0.0, 0.0)
        sim.activity_manager.move_people_to_active_subgroups(
            ["medical_facility", "primary_activity", "residence"],
        )
        assert worker in worker.medical_facility.people
        assert pupil in pupil.primary_activity.people
        worker.health_information = None
        sim.clear_world()

    def test__default_policy_kids(self,  selector, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        permanent_policy = SevereSymptomsStayHome()
        policies = Policies([permanent_policy])
        sim.activity_manager.policies = policies
        sim.clear_world()
        sim.activity_manager.move_people_to_active_subgroups(
            ["primary_activity", "residence"],
        )
        date = datetime(2019, 2, 1)
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()
        infect_person(pupil, selector, "severe")
        sim.update_health_status(0.0, 0.0)
        assert pupil.health_information.tag == SymptomTag.severe
        sim.activity_manager.move_people_to_active_subgroups(
            ["primary_activity", "residence"],
        )
        assert pupil in pupil.residence.people
        assert worker in worker.residence.people
        pupil.health_information = None
        sim.clear_world()


class TestClosure:
    def test__close_schools(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
        school_closure = CloseSchools(
            start_time="2020-1-1", end_time="2020-10-1", years_to_close=[6],
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
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_during_policy
        )
        assert individual_policies.apply(
            person=pupil, activities=activities, days_from_start=0
        ) == ["residence",]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert pupil in pupil.residence.people
        assert worker in worker.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_after_policy
        )
        assert individual_policies.apply(
            person=pupil, activities=activities, days_from_start=0
        ) == ["primary_activity", "residence",]
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
        individual_policies = IndividualPolicies.get_active_policies(
            policies=policies, date=time_during_policy
        )
        assert individual_policies.apply(
            person=pupil, activities=activities, days_from_start=0
        ) == ["primary_activity", "residence",]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        individual_policies = IndividualPolicies.get_active_policies(
            policies=policies, date=time_after_policy
        )
        assert individual_policies.apply(
            person=pupil, activities=activities, days_from_start=0
        ) == ["primary_activity", "residence",]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__close_universities(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
        university_closure = CloseUniversities(
            start_time="2020-1-1", end_time="2020-10-1",
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
        individual_policies = IndividualPolicies.get_active_policies(
            policies=policies, date=time_during_policy
        )
        assert individual_policies.apply(
            person=student, activities=activities, days_from_start=0
        ) == ["residence",]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert student in student.residence.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        individual_policies = IndividualPolicies.get_active_policies(
            policies=policies, date=time_after_policy
        )
        assert individual_policies.apply(
            person=student, activities=activities, days_from_start=0
        ) == ["primary_activity", "residence"]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert student in student.primary_activity.people
        sim.clear_world()

    def test__close_companies(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
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
        individual_policies = IndividualPolicies.get_active_policies(
            policies=policies, date=time_during_policy
        )
        assert individual_policies.apply(
            person=worker, activities=activities, days_from_start=0
        ) == ["residence"]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert worker in worker.residence.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        individual_policies = IndividualPolicies.get_active_policies(
            policies=policies, date=time_after_policy
        )
        assert individual_policies.apply(
            person=worker, activities=activities, days_from_start=0
        ) == ["commute", "primary_activity", "residence"]
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
        individual_policies = IndividualPolicies.get_active_policies(
            policies=policies, date=time_during_policy
        )
        assert individual_policies.apply(
            person=worker, activities=activities, days_from_start=0
        ) == ["commute", "primary_activity", "residence"]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        individual_policies = IndividualPolicies.get_active_policies(
            policies=policies, date=time_after_policy
        )
        assert individual_policies.apply(
            person=worker, activities=activities, days_from_start=0
        ) == ["commute", "primary_activity", "residence"]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__close_companies_frequency_of_randoms(
        self, setup_policy_world
    ):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
        company_closure = CloseCompanies(
            start_time="2020-1-1",
            end_time="2020-10-1",
            avoid_work_probability=0.2
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
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_during_policy
        )
        # Move the person 1_0000 times for five days
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in individual_policies.apply(
                    person=worker, activities=activities, days_from_start=0
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(4.0, rel=0.1)
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(10):
                if "primary_activity" in individual_policies.apply(
                    person=worker, activities=activities, days_from_start=0
                ):
                    n_days += 0.5
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(4.0, rel=0.1)

        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_after_policy
        )
        assert individual_policies.apply(
            person=worker, activities=activities, days_from_start=0
        ) == ["commute", "primary_activity", "residence",]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__close_companies_frequency_of_furlough_ratio(
        self, setup_policy_world
    ):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
        company_closure = CloseCompanies(
            start_time="2020-1-1",
            end_time="2020-10-1",
            furlough_probability=0.2
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
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_during_policy
        )
        # Move the person 1_0000 times for five days

        # Testing key_ratio and key_worker feature in random_ratio
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in individual_policies.apply(
                        person=worker, activities=activities, days_from_start=0, furlough_ratio=0.,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(0., rel=0.1)
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in individual_policies.apply(
                    person=worker, activities=activities, days_from_start=0, furlough_ratio=0.1,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(0., rel=0.1)
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in individual_policies.apply(
                    person=worker, activities=activities, days_from_start=0, furlough_ratio=0.4,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(2.5, rel=0.1)

        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_after_policy
        )
        assert individual_policies.apply(
            person=worker, activities=activities, days_from_start=0
        ) == ["commute", "primary_activity", "residence",]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__close_companies_frequency_of_random_ratio(
        self, setup_policy_world
    ):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
        company_closure = CloseCompanies(
            start_time="2020-1-1",
            end_time="2020-10-1",
            avoid_work_probability=0.2,
            key_probability=0.2,
            furlough_probability=0.2
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
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_during_policy
        )
        # Move the person 1_0000 times for five days

        # Testing key_ratio feature in random_ratio
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in individual_policies.apply(
                        person=worker, activities=activities, days_from_start=0, key_ratio=0.,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(5.0, rel=0.1)
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in individual_policies.apply(
                    person=worker, activities=activities, days_from_start=0, key_ratio=0.1,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(4.5, rel=0.1)
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in individual_policies.apply(
                    person=worker, activities=activities, days_from_start=0, key_ratio=0.2,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(4.0, rel=0.1)

        # Testing furlough_ratio feature in random_ratio
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in individual_policies.apply(
                        person=worker, activities=activities, days_from_start=0, furlough_ratio=0.,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(0., rel=0.1)
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in individual_policies.apply(
                        person=worker, activities=activities, days_from_start=0, furlough_ratio=0.1,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(2.0, rel=0.1)
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in individual_policies.apply(
                        person=worker, activities=activities, days_from_start=0, furlough_ratio=0.3,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(4.0, rel=0.1)

        # Testing furlough_ratio and key_ratio mixing feature in random_ratio
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in individual_policies.apply(
                        person=worker, activities=activities, days_from_start=0, key_ratio=0., furlough_ratio=0.,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(0., rel=0.1)
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in individual_policies.apply(
                        person=worker, activities=activities, days_from_start=0, key_ratio=0., furlough_ratio=0.1,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(2.5, rel=0.1)
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in individual_policies.apply(
                        person=worker, activities=activities, days_from_start=0, key_ratio=0.1, furlough_ratio=0.1,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(2.0, rel=0.1)
        n_days_in_week = []
        for i in range(500):
            n_days = 0
            for j in range(5):
                if "primary_activity" in individual_policies.apply(
                        person=worker, activities=activities, days_from_start=0, key_ratio=0.3, furlough_ratio=0.3,
                ):
                    n_days += 1.0
            n_days_in_week.append(n_days)
        assert np.mean(n_days_in_week) == pytest.approx(4.0, rel=0.1)
        
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_after_policy
        )
        assert individual_policies.apply(
            person=worker, activities=activities, days_from_start=0
        ) == ["commute", "primary_activity", "residence",]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy
        )
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__close_companies_full_closure(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
        company_closure = CloseCompanies(
            start_time="2020-1-1", end_time="2020-10-1", full_closure=True,
        )
        policies = Policies([company_closure])
        sim.activity_manager.policies = policies
        worker.lockdown_status = "key_worker"
        activities = ["commute", "primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_during_policy
        )
        assert individual_policies.apply(
            person=worker, activities=activities, days_from_start=0
        ) == ["residence"]
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert worker in worker.residence.people
        sim.clear_world()


class TestShielding:
    def test__old_people_shield(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
        shielding = Shielding(start_time="2020-1-1", end_time="2020-10-1", min_age=30)
        policies = Policies([shielding])
        sim.activity_manager.policies = policies
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_during_policy
        )
        assert "primary_activity" not in individual_policies.apply(
            person=worker, activities=activities, days_from_start=0
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy
        )
        assert worker in worker.residence.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()

    def test__old_people_shield_with_compliance(
        self, setup_policy_world
    ):
        world, pupil, student, worker, _ = setup_policy_world
        super_area = world.super_areas[0]
        shielding = Shielding(
            start_time="2020-1-1", end_time="2020-10-1", min_age=30, compliance=0.6
        )
        policies = Policies([shielding])
        activities = ["primary_activity", "residence"]
        time_during_policy = datetime(2020, 2, 1)
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_during_policy
        )
        compliant_days = 0
        for i in range(100):
            if "primary_activity" not in individual_policies.apply(
                person=worker, activities=activities, days_from_start=0
            ):
                compliant_days += 1

        assert compliant_days / 100 == pytest.approx(shielding.compliance, abs=0.1)


class TestQuarantine:
    def test__symptomatic_stays_for_one_week(self, setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
        quarantine = Quarantine(
            start_time="2020-1-1", end_time="2020-1-30", n_days=7, n_days_household=14,
        )
        policies = Policies([quarantine])
        sim.activity_manager.policies = policies
        infect_person(worker, selector, "mild")
        sim.update_health_status(0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        individual_policies = IndividualPolicies.get_active_policies(
            policies=policies, date=time_during_policy
        )
        assert "primary_activity" not in individual_policies.apply(
            person=worker, activities=activities, days_from_start=6
        )
        assert "primary_activity" in individual_policies.apply(
            person=worker, activities=activities, days_from_start=20
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
        worker.health_information = None
        sim.clear_world()

    def test__asymptomatic_is_free(self, setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
        quarantine = Quarantine(
            start_time="2020-1-1", end_time="2020-1-30", n_days=7, n_days_household=14,
        )
        policies = Policies([quarantine])
        sim.activity_manager.policies = policies
        infect_person(worker, selector, "asymptomatic")
        sim.update_health_status(0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_during_policy
        )
        assert "primary_activity" in individual_policies.apply(
            person=worker, activities=activities, days_from_start=6.0
        )
        worker.health_information = None
        sim.clear_world()

    def test__housemates_stay_for_two_weeks(self, setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
        quarantine = Quarantine(
            start_time="2020-1-1", end_time="2020-1-30", n_days=7, n_days_household=14,
        )
        policies = Policies([quarantine])
        sim.activity_manager.policies = policies
        infect_person(worker, selector, "mild")
        sim.update_health_status(0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        # before symptoms onset
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_during_policy
        )
        assert "primary_activity" not in individual_policies.apply(
            person=pupil, activities=activities, days_from_start=8.0
        )
        # after symptoms onset
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy, 8.0
        )
        assert pupil in pupil.residence.people
        # more thatn two weeks after symptoms onset
        assert "primary_activity" in individual_policies.apply(
            person=pupil, activities=activities, days_from_start=25
        )
        worker.health_information = None
        sim.clear_world()
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy, 25
        )
        assert pupil in pupil.primary_activity.people
        sim.clear_world()

    def test__housemates_of_asymptomatic_are_free(
        self, setup_policy_world, selector
    ):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
        quarantine = Quarantine(
            start_time="2020-1-1", end_time="2020-1-30", n_days=7, n_days_household=14,
        )
        policies = Policies([quarantine])
        sim.activity_manager.policies = policies
        infect_person(worker, selector, "asymptomatic")
        sim.update_health_status(0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        # after symptoms onset
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_during_policy
        )
        assert "primary_activity" in individual_policies.apply(
            person=pupil, activities=activities, days_from_start=8.0
        )
        assert "primary_activity" in individual_policies.apply(
            person=pupil, activities=activities, days_from_start=25.0
        )
        worker.health_information = None
        sim.clear_world()

    def test__quarantine_zero_complacency(self, setup_policy_world, selector):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
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
        sim.update_health_status(0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        individual_policies = IndividualPolicies.get_active_policies(
            policies, date=time_during_policy
        )
        # before symptoms onset
        assert "primary_activity" in individual_policies.apply(
            person=pupil, activities=activities, days_from_start=4.0
        )
        # after symptoms onset
        assert "primary_activity" in individual_policies.apply(
            person=pupil, activities=activities, days_from_start=8.0
        )
        # more thatn two weeks after symptoms onset
        assert "primary_activity" in individual_policies.apply(
            person=pupil, activities=activities, days_from_start=25
        )
        worker.health_information = None
        sim.clear_world()

def test__kid_at_home_is_supervised(setup_policy_world, selector):
    world, pupil, student, worker, sim = setup_policy_world
    policies = Policies([SevereSymptomsStayHome()])
    sim.activity_manager.policies = policies
    assert pupil.primary_activity is not None
    infect_person(pupil, selector, "severe")
    assert pupil.health_information.tag == SymptomTag.severe
    sim.activity_manager.move_people_to_active_subgroups(
        ["primary_activity", "residence"]
    )
    assert pupil in pupil.residence.people
    guardians_at_home = [
        person for person in pupil.residence.group.people if person.age >= 18
    ]
    assert len(guardians_at_home) != 0
    sim.clear_world()

