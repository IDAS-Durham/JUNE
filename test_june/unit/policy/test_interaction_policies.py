import copy
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
    SocialDistancing,
    Hospitalisation,
    InteractionPolicies,
    MaskWearing,
)
from june.simulator import Simulator
from june.world import World

test_config = paths.configs_path / "tests/test_simulator_simple.yaml"


class TestSocialDistancing:
    def test__social_distancing(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        world.cemeteries = Cemeteries()
        start_date = datetime(2020, 3, 10)
        end_date = datetime(2020, 3, 12)
        beta_factors = {
            "box": 0.7,
            "pub": 0.7,
            "grocery": 0.7,
            "cinema": 0.7,
            "inter_city_transport": 0.7,
            "city_transport": 0.7,
            "hospital": 0.7,
            "care_home": 0.7,
            "company": 0.7,
            "school": 0.7,
            "household": 1.0,
            "university": 0.7,
        }
        social_distance = SocialDistancing(
            start_time="2020-03-10", end_time="2020-03-12", beta_factors=beta_factors
        )
        beta_factors2 = {"cinema": 4}
        start_date2 = datetime(2020, 3, 12)
        end_date2 = datetime(2020, 3, 15)
        social_distance2 = SocialDistancing(
            start_time="2020-03-12", end_time="2020-03-15", beta_factors=beta_factors2
        )
        policies = Policies([social_distance, social_distance2])
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        leisure_instance.distribute_social_venues_to_areas(
            world.areas, super_areas=world.super_areas
        )
        sim.activity_manager.policies = policies
        sim.activity_manager.leisure = leisure_instance
        sim.timer.reset()
        initial_betas = copy.deepcopy(sim.interaction.beta)
        sim.clear_world()
        while sim.timer.date <= sim.timer.final_date:
            sim.do_timestep()
            if sim.timer.date >= start_date and sim.timer.date < end_date:
                for group in sim.interaction.beta:
                    if group != "household":
                        assert sim.interaction.beta[group] == initial_betas[group] * 0.7
                    else:
                        assert sim.interaction.beta[group] == initial_betas[group]
                next(sim.timer)
                continue
            if sim.timer.date >= start_date2 and sim.timer.date < end_date2:
                for group in sim.interaction.beta:
                    if group != "cinema":
                        assert sim.interaction.beta == 4.0
                    else:
                        assert sim.interaction.beta[group] == initial_betas[group]
                next(sim.timer)
                continue
            assert sim.interaction.beta == initial_betas
            next(sim.timer)

    def test__social_distancing_regional_compliance(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        regional_compliance = [{
                'start_time': '2020-02-10',
                'end_time': '2021-12-01',
                worker.region.name: 0.
        }]
        world.cemeteries = Cemeteries()
        start_date = datetime(2020, 3, 10)
        end_date = datetime(2020, 3, 12)
        beta_factors = {
            "box": 0.7,
            "pub": 0.7,
            "grocery": 0.7,
            "cinema": 0.7,
            "inter_city_transport": 0.7,
            "city_transport": 0.7,
            "hospital": 0.7,
            "care_home": 0.7,
            "company": 0.7,
            "school": 0.7,
            "household": 1.0,
            "university": 0.7,
        }
        social_distance = SocialDistancing(
            start_time="2020-03-10", end_time="2020-03-12", beta_factors=beta_factors
        )
        policies = Policies([social_distance],
                regional_compliance=regional_compliance)
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        leisure_instance.distribute_social_venues_to_areas(
            world.areas, super_areas=world.super_areas
        )
        sim.activity_manager.policies = policies
        sim.activity_manager.leisure = leisure_instance
        sim.timer.reset()
        initial_betas = copy.deepcopy(sim.interaction.beta)
        sim.clear_world()
        company = Company(super_area=world.super_areas[0])
        household = Household(area=world.areas[0])
        while sim.timer.date <= sim.timer.final_date:
            sim.do_timestep()
            if sim.timer.date >= start_date and sim.timer.date < end_date:
                assert sim.interaction.get_beta_for_group(group=company) == initial_betas['company']
                assert sim.interaction.get_beta_for_group(group=household) == initial_betas['household']
                next(sim.timer)
                continue
            assert sim.interaction.beta == initial_betas
            next(sim.timer)


class TestMaskWearing:
    def test__mask_wearing(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        world.cemeteries = Cemeteries()
        start_date = datetime(2020, 3, 10)
        end_date = datetime(2020, 3, 12)
        compliance = 1.0
        beta_factor = 0.5
        mask_probabilities = {
            "box": 0.5,
            "pub": 0.5,
            "grocery": 0.5,
            "cinema": 0.5,
            "city_transport": 0.5,
            "inter_city_transport": 0.5,
            "hospital": 0.5,
            "care_home": 0.5,
            "company": 0.5,
            "school": 0.5,
            "household": 0.0,
            "university": 0.5,
        }
        mask_wearing = MaskWearing(
            start_time="2020-03-10",
            end_time="2020-03-12",
            beta_factor=beta_factor,
            mask_probabilities=mask_probabilities,
            compliance=compliance,
        )
        policies = Policies([mask_wearing])
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        leisure_instance.distribute_social_venues_to_areas(
            world.areas, super_areas=world.super_areas
        )
        sim.activity_manager.policies = policies
        sim.activity_manager.leisure = leisure_instance
        sim.timer.reset()
        initial_betas = copy.deepcopy(sim.interaction.beta)
        sim.clear_world()
        while sim.timer.date <= sim.timer.final_date:
            sim.do_timestep()
            if sim.timer.date >= start_date and sim.timer.date < end_date:
                for group in sim.interaction.beta:
                    if group != "household":
                        assert sim.interaction.beta[group] == initial_betas[group] * (
                            1 - (0.5 * 1.0 * (1 - 0.5))
                        )
                    else:
                        assert sim.interaction.beta[group] == initial_betas[group]
                next(sim.timer)
                continue
            assert sim.interaction.beta == initial_betas
            next(sim.timer)
