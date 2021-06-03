from datetime import datetime, timedelta
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
from june.groups.leisure import (
    Cinemas,
    Pubs,
    Cinema,
    Pub,
    generate_leisure_for_config,
    generate_leisure_for_world,
)
from june.epidemiology.infection import SymptomTag
from june.epidemiology.infection.infection_selector import InfectionSelector
from june.interaction import Interaction
from june.policy import (
    Policy,
    Policies,
    CloseLeisureVenue,
    ChangeLeisureProbability,
    LeisurePolicies,
    TieredLockdown,
    TieredLockdowns,
    ChangeVisitsProbability,
)
from june.simulator import Simulator
from june.world import World


test_config = paths.configs_path / "tests/test_simulator_simple.yaml"


class TestCloseLeisure:
    def test__close_leisure_venues(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        close_venues = CloseLeisureVenue(
            start_time="2020-3-1",
            end_time="2020-3-30",
            venues_to_close=["pub"],
        )
        policies = Policies([close_venues])
        leisure = generate_leisure_for_config(world=world, config_filename=test_config)
        leisure.distribute_social_venues_to_areas(
            world.areas, super_areas=world.super_areas
        )
        sim.activity_manager.leisure = leisure
        sim.activity_manager.policies = policies
        sim.clear_world()
        time_before_policy = datetime(2019, 2, 1)
        activities = ["leisure", "residence"]
        leisure.generate_leisure_probabilities_for_timestep(
            delta_time=10000, working_hours=False, day_type="weekday"
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_before_policy, 0.0
        )
        assert worker in worker.leisure.people
        sim.clear_world()
        time_during_policy = datetime(2020, 3, 14)
        policies.leisure_policies.apply(date=time_during_policy, leisure=leisure)
        assert list(world.regions[0].policy["global_closed_venues"]) == ["pub"]
        leisure.generate_leisure_probabilities_for_timestep(
            delta_time=10000, working_hours=False, day_type="weekday"
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy, 0.0
        )
        assert (
            worker in worker.leisure.people and worker.leisure.group.spec == "cinema"
        ) or worker in worker.residence.people
        sim.clear_world()

        sim.clear_world()
        time_after_policy = datetime(2020, 3, 30)
        policies.leisure_policies.apply(date=time_after_policy, leisure=leisure)
        assert list(world.regions[0].policy["global_closed_venues"]) == []
        leisure.generate_leisure_probabilities_for_timestep(
            delta_time=10000, working_hours=False, day_type="weekday"
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy, 0.0
        )
        assert worker in worker.leisure.people

    def test__close_leisure_venues_tiered_lockdowns(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        tiered_lockdown = TieredLockdown(
            start_time="2020-03-01",
            end_time="2020-03-30",
            tiers_per_region={"North East": 4.},
        )
        tiered_lockdowns = TieredLockdowns([tiered_lockdown])

        policies = Policies([tiered_lockdowns])
        leisure = generate_leisure_for_config(world=world, config_filename=test_config)
        leisure.distribute_social_venues_to_areas(
            world.areas, super_areas=world.super_areas
        )
        sim.activity_manager.leisure = leisure
        sim.activity_manager.policies = policies
        sim.clear_world()
        time_before_policy = datetime(2019, 2, 1)
        activities = ["leisure", "residence"]
        leisure.generate_leisure_probabilities_for_timestep(
            delta_time=10000, working_hours=False, day_type="weekday"
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_before_policy, 0.0
        )
        assert worker in worker.leisure.people
        sim.clear_world()
        time_during_policy = datetime(2020, 3, 14)
        policies.tiered_lockdown.apply(date=time_during_policy, regions=world.regions)
        assert "pub" in list(world.regions[0].policy["local_closed_venues"])
        assert "cinema" in list(world.regions[0].policy["local_closed_venues"])
        leisure.generate_leisure_probabilities_for_timestep(
            delta_time=10000, working_hours=False, day_type="weekday"
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_during_policy, 0.0
        )
        assert worker in worker.residence.people
        sim.clear_world()

        sim.clear_world()
        time_after_policy = datetime(2020, 3, 30)
        policies.tiered_lockdown.apply(date=time_after_policy, regions=world.regions)
        assert list(world.regions[0].policy["local_closed_venues"]) == []
        leisure.generate_leisure_probabilities_for_timestep(
            delta_time=10000, working_hours=False, day_type="weekday"
        )
        sim.activity_manager.move_people_to_active_subgroups(
            activities, time_after_policy, 0.0
        )
        assert worker in worker.leisure.people


class TestReduceLeisureProbabilities:
    def test__reduce_household_visits(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
        leisure = generate_leisure_for_config(world=world, config_filename=test_config)
        reduce_leisure_probabilities = ChangeLeisureProbability(
            start_time="2020-03-02",
            end_time="2020-03-05",
            activity_reductions={
                "pub": {
                    "male": {"0-50": 0.5, "50-100": 0.0},
                    "female": {"0-100": 0.5},
                },
            },
        )
        policies = Policies([reduce_leisure_probabilities])
        sim.activity_manager.policies = policies
        sim.activity_manager.leisure = leisure
        sim.clear_world()
        policies.leisure_policies.apply(
            date=sim.timer.date, leisure=sim.activity_manager.leisure
        )
        sim.activity_manager.leisure.generate_leisure_probabilities_for_timestep(
            0.1, working_hours=False, day_type="weekday"
        )
        assert str(sim.timer.date.date()) == "2020-03-01"
        household = Household()
        household.area = super_area.areas[0]
        leisure.distribute_social_venues_to_areas(
            world.areas, super_areas=world.super_areas
        )
        person1 = Person.from_attributes(age=60, sex="m")
        person1.area = super_area.areas[0]
        household.add(person1)
        person2 = Person.from_attributes(age=19, sex="f")
        person2.area = super_area.areas[0]
        leisure.distribute_social_venues_to_areas(
            world.areas, super_areas=world.super_areas
        )
        household.add(person2)
        pubs1_visits_before = 0
        pubs2_visits_before = 0
        for _ in range(5000):
            subgroup = leisure.get_subgroup_for_person_and_housemates(person1)
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs1_visits_before += 1
            person1.subgroups.leisure = None
            subgroup = leisure.get_subgroup_for_person_and_housemates(person2)
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs2_visits_before += 1
            person2.subgroups.leisure = None
        assert pubs1_visits_before > 0
        assert pubs2_visits_before > 0
        # next day leisure policies are
        while str(sim.timer.date.date()) != "2020-03-02":
            next(sim.timer)
        policies.leisure_policies.apply(date=sim.timer.date, leisure=leisure)
        leisure.generate_leisure_probabilities_for_timestep(
            0.1, working_hours=False, day_type="weekday"
        )
        assert leisure.policy_reductions["pub"]["weekday"]["m"][60] == 0.0
        assert leisure.policy_reductions["pub"]["weekday"]["f"][19] == 0.5
        assert leisure.policy_reductions["pub"]["weekend"]["m"][60] == 0.0
        assert leisure.policy_reductions["pub"]["weekend"]["f"][19] == 0.5
        pubs1_visits_after = 0
        pubs2_visits_after = 0
        for _ in range(5000):
            subgroup = leisure.get_subgroup_for_person_and_housemates(person1)
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs1_visits_after += 1
            person1.subgroups.leisure = None
            subgroup = leisure.get_subgroup_for_person_and_housemates(person2)
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs2_visits_after += 1
            person2.subgroups.leisure = None
        assert pubs1_visits_after == 0
        assert np.isclose(pubs2_visits_after / pubs2_visits_before, 0.5, rtol=0.1)
        # end of policy
        while str(sim.timer.date.date()) != "2020-03-05":
            next(sim.timer)
        policies.leisure_policies.apply(
            date=sim.timer.date, leisure=sim.activity_manager.leisure
        )
        sim.activity_manager.leisure.generate_leisure_probabilities_for_timestep(
            0.1, working_hours=False, day_type="weekday"
        )
        assert leisure.policy_reductions == {}
        assert leisure.policy_reductions == {}
        pubs1_visits_restored = 0
        pubs2_visits_restored = 0
        for _ in range(5000):
            subgroup = leisure.get_subgroup_for_person_and_housemates(person1)
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs1_visits_restored += 1
            person1.subgroups.leisure = None
            subgroup = leisure.get_subgroup_for_person_and_housemates(person2)
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs2_visits_restored += 1
            person2.subgroups.leisure = None
        assert np.isclose(pubs1_visits_restored, pubs1_visits_before, rtol=0.1)
        assert np.isclose(pubs2_visits_restored, pubs2_visits_before, rtol=0.1)
        assert leisure.policy_reductions == {}

    def test__reduce_household_visits_with_regional_compliance(
        self, setup_policy_world
    ):
        world, pupil, student, worker, sim = setup_policy_world
        while str(sim.timer.date.date()) != "2020-03-02":
            next(sim.timer)
        super_area = world.super_areas[0]
        region = worker.region
        leisure = generate_leisure_for_config(world=world, config_filename=test_config)
        assert leisure.regions[0] == region
        reduce_leisure_probabilities = ChangeLeisureProbability(
            start_time="2020-03-02",
            end_time="2020-03-05",
            activity_reductions={
                "pub": {
                    "male": {"0-50": 0.5, "50-100": 0.0},
                    "female": {"0-100": 0.5},
                },
            },
        )
        policies = Policies([reduce_leisure_probabilities])
        sim.activity_manager.policies = policies
        sim.activity_manager.leisure = leisure

        # compliance to 1
        policies.leisure_policies.apply(date=sim.timer.date, leisure=leisure)
        assert leisure.policy_reductions["pub"]["weekday"]["m"][60] == 0.0
        assert leisure.policy_reductions["pub"]["weekday"]["f"][40] == 0.5
        assert leisure.policy_reductions["pub"]["weekend"]["m"][60] == 0.0
        assert leisure.policy_reductions["pub"]["weekend"]["f"][40] == 0.5
        original_poisson_parameter = leisure.leisure_distributors[
            "pub"
        ].get_poisson_parameter(
            sex="m", age=25, day_type="weekday", working_hours=False
        )
        full_comp_poisson_parameter = leisure._get_activity_poisson_parameter(
            activity="pub",
            distributor=leisure.leisure_distributors["pub"],
            sex="m",
            age=25,
            day_type="weekday",
            working_hours=False,
            region=region,
        )
        region.regional_compliance = 0.5
        half_comp_poisson_parameter = leisure._get_activity_poisson_parameter(
            activity="pub",
            distributor=leisure.leisure_distributors["pub"],
            sex="m",
            age=25,
            day_type="weekday",
            working_hours=False,
            region=region,
        )
        assert np.isclose(full_comp_poisson_parameter, 0.5 * original_poisson_parameter)
        assert np.isclose(
            half_comp_poisson_parameter,
            original_poisson_parameter
            + 0.5 * (full_comp_poisson_parameter - original_poisson_parameter),
        )

        # check integration with region object
        region.regional_compliance = 1.0
        leisure.generate_leisure_probabilities_for_timestep(
            delta_time=0.1, working_hours=False, day_type="weekday"
        )
        full_comp_probs = leisure._get_activity_probabilities_for_person(person=worker)
        region.regional_compliance = 0.5
        leisure.generate_leisure_probabilities_for_timestep(
            delta_time=0.1, working_hours=False, day_type="weekday"
        )
        half_comp_probs = leisure._get_activity_probabilities_for_person(person=worker)
        # this is  a reduction, so being less compliant means you go more often
        assert half_comp_probs["does_activity"] > full_comp_probs["does_activity"]
        assert (
            half_comp_probs["activities"]["pub"] > full_comp_probs["activities"]["pub"]
        )
        assert (
            half_comp_probs["drags_household"]["pub"]
            == full_comp_probs["drags_household"]["pub"]
        )


class TestChangeVisitsProbabilities:
    def test__change_split(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        super_area = world.super_areas[0]
        leisure = generate_leisure_for_world(
            world=world, list_of_leisure_groups=["care_home_visits", "household_visits"]
        )
        reduce_leisure_probabilities = ChangeVisitsProbability(
            start_time="2020-03-02",
            end_time="2020-03-05",
            new_residence_type_probabilities={"household": 0.9, "care_home": 0.1},
        )
        policies = Policies([reduce_leisure_probabilities])
        assert leisure.leisure_distributors[
            "residence_visits"
        ].residence_type_probabilities == {"household": 0.66, "care_home": 0.34}
        starting_date = datetime(2020, 2, 25)
        ending_date = datetime(2020, 4, 1)
        current_date = starting_date
        checks1 = False
        checks2 = False
        while current_date < ending_date:
            policies.leisure_policies.apply(date=current_date, leisure=leisure)
            if current_date < datetime(2020, 3, 2) or current_date >= datetime(
                2020, 3, 5
            ):
                assert (
                    leisure.leisure_distributors["residence_visits"].policy_reductions
                    == {}
                )
                checks1 = True
            else:
                assert leisure.leisure_distributors[
                    "residence_visits"
                ].policy_reductions == {"household": 0.9, "care_home": 0.1}
                checks2 = True
            current_date += timedelta(days=1)
        assert checks1 and checks2
