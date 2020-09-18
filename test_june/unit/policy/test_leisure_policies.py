from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from june import paths
from june.demography import Person, Population
from june.geography import Geography
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
from june.infection.infection_selector import InfectionSelector
from june.interaction import Interaction
from june.policy import (
    Policy,
    Policies,
    CloseLeisureVenue,
    ChangeLeisureProbability,
    LeisurePolicies,
)
from june.simulator import Simulator
from june.world import World


test_config = paths.configs_path / "tests/test_simulator_simple.yaml"


class TestCloseLeisure:
    def test__close_leisure_venues(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        close_venues = CloseLeisureVenue(
            start_time="2020-3-1", end_time="2020-3-30", venues_to_close=["pub"],
        )
        policies = Policies([close_venues])
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        leisure_instance.distribute_social_venues_to_areas(
            world.areas, super_areas=world.super_areas
        )
        sim.activity_manager.leisure = leisure_instance
        sim.activity_manager.policies = policies
        sim.activity_manager.leisure.leisure_distributors["pubs"].weekend_boost = 5000
        sim.clear_world()
        time_before_policy = datetime(2019, 2, 1)
        activities = ["leisure", "residence"]
        sim.activity_manager.leisure.generate_leisure_probabilities_for_timestep(
            10000, False, False
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_before_policy, 0.0
        )
        assert worker in worker.leisure.people
        sim.clear_world()
        time_during_policy = datetime(2020, 3, 14)
        policies.leisure_policies.apply(
            date=time_during_policy, leisure=leisure_instance
        )
        assert list(leisure_instance.closed_venues) == ["pub"]
        sim.activity_manager.leisure.generate_leisure_probabilities_for_timestep(
            10000, False, False
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy, 0.0
        )
        assert (
            worker in worker.leisure.people and worker.leisure.group.spec == "cinema"
        ) or worker in worker.residence.people
        sim.clear_world()
        
        sim.clear_world()
        time_after_policy = datetime(2020, 3,30)
        policies.leisure_policies.apply(
            date=time_after_policy, leisure=leisure_instance
        )
        assert list(leisure_instance.closed_venues) == []
        sim.activity_manager.leisure.generate_leisure_probabilities_for_timestep(
            10000, False, False
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy , 0.0
        )
        assert worker in worker.leisure.people


class TestReduceLeisureProbabilities:
    def test__reduce_household_visits(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        reduce_leisure_probabilities = ChangeLeisureProbability(
            start_time="2020-03-02",
            end_time="2020-03-05",
            leisure_activities_probabilities={
                "pubs": {"men": {"0-50": 0.2, "50-100": 0.0}, "women": {"0-100": 0.2},},
            },
        )
        policies = Policies([reduce_leisure_probabilities])
        sim.activity_manager.policies = policies
        sim.activity_manager.leisure = leisure_instance
        sim.clear_world()
        policies.leisure_policies.apply(
            date=sim.timer.date, leisure=sim.activity_manager.leisure
        )
        sim.activity_manager.leisure.generate_leisure_probabilities_for_timestep(
            0.1, False, False
        )
        original_male_pub_probabilities = sim.activity_manager.leisure.leisure_distributors[
            "pubs"
        ].male_probabilities
        original_female_pub_probabilities = sim.activity_manager.leisure.leisure_distributors[
            "pubs"
        ].female_probabilities
        assert str(sim.timer.date.date()) == "2020-03-01"
        household = Household()
        household.area = super_area.areas[0]
        leisure_instance.distribute_social_venues_to_areas(
            world.areas, super_areas=world.super_areas
        )
        person1 = Person.from_attributes(age=60, sex="m")
        person1.area = super_area.areas[0]
        household.add(person1)
        person2 = Person.from_attributes(age=80, sex="f")
        person2.area = super_area.areas[0]
        sim.activity_manager.leisure.distribute_social_venues_to_areas(
            world.areas, super_areas=world.super_areas
        )
        household.add(person2)
        pubs1_visits_before = 0
        pubs2_visits_before = 0
        for _ in range(5000):
            subgroup = sim.activity_manager.leisure.get_subgroup_for_person_and_housemates(
                person1
            )
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs1_visits_before += 1
            person1.subgroups.leisure = None
            subgroup = sim.activity_manager.leisure.get_subgroup_for_person_and_housemates(
                person2
            )
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs2_visits_before += 1
            person2.subgroups.leisure = None
        assert pubs1_visits_before > 0
        assert pubs2_visits_before > 0
        # next day leisure policies are
        while str(sim.timer.date.date()) != "2020-03-02":
            next(sim.timer)
        policies.leisure_policies.apply(
            date=sim.timer.date, leisure=sim.activity_manager.leisure
        )
        sim.activity_manager.leisure.generate_leisure_probabilities_for_timestep(
            0.1, False, False
        )
        assert (
            sim.activity_manager.leisure.leisure_distributors[
                "pubs"
            ].male_probabilities[60]
            == 0.0
        )
        assert (
            sim.activity_manager.leisure.leisure_distributors[
                "pubs"
            ].female_probabilities[60]
            == 0.2
        )
        pubs1_visits_after = 0
        pubs2_visits_after = 0
        for _ in range(5000):
            subgroup = sim.activity_manager.leisure.get_subgroup_for_person_and_housemates(
                person1
            )
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs1_visits_after += 1
            person1.subgroups.leisure = None
            subgroup = sim.activity_manager.leisure.get_subgroup_for_person_and_housemates(
                person2
            )
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs2_visits_after += 1
            person2.subgroups.leisure = None
        assert pubs1_visits_after == 0
        assert 0 < pubs2_visits_after < pubs2_visits_before
        # end of policy
        while str(sim.timer.date.date()) != "2020-03-05":
            next(sim.timer)
        policies.leisure_policies.apply(
            date=sim.timer.date, leisure=sim.activity_manager.leisure
        )
        sim.activity_manager.leisure.generate_leisure_probabilities_for_timestep(
            0.1, False, False
        )
        pubs1_visits_restored = 0
        pubs2_visits_restored = 0
        for _ in range(5000):
            subgroup = sim.activity_manager.leisure.get_subgroup_for_person_and_housemates(
                person1
            )
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs1_visits_restored += 1
            person1.subgroups.leisure = None
            subgroup = sim.activity_manager.leisure.get_subgroup_for_person_and_housemates(
                person2
            )
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs2_visits_restored += 1
            person2.subgroups.leisure = None
        assert np.isclose(pubs1_visits_restored, pubs1_visits_before, rtol=0.2)
        assert np.isclose(pubs2_visits_restored, pubs2_visits_before, rtol=0.2)
        assert (
            sim.activity_manager.leisure.leisure_distributors["pubs"].male_probabilities
            == original_male_pub_probabilities
        )
        assert (
            sim.activity_manager.leisure.leisure_distributors[
                "pubs"
            ].female_probabilities
            == original_female_pub_probabilities
        )
