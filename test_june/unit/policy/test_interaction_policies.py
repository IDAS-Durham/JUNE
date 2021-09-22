import copy
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from june import paths
from june.demography import Person, Population
from june.geography import Geography, Cities
from june.groups import Hospital, School, Company, Household, University
from june.groups import (
    Hospitals,
    Schools,
    Companies,
    Households,
    Universities,
    Cemeteries,
    Cinemas,
    Pubs,
    Cinema,
    Pub,
    InteractiveSchool,
    InteractiveCompany,
    InteractiveHousehold,
)
from june.groups.leisure import (
    Leisure,
    generate_leisure_for_config,
    generate_leisure_for_world,
)
from june.groups.group.interactive import InteractiveGroup
from june.epidemiology.infection import SymptomTag
from june.epidemiology.infection.infection_selector import InfectionSelector
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
    @pytest.fixture(name="social_distancing_sim")
    def setup(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        world.cemeteries = Cemeteries()
        beta_factors = {
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
            "household_visits": 0.5,
        }
        social_distance = SocialDistancing(
            start_time="2020-03-02", end_time="2020-03-05", beta_factors=beta_factors
        )
        beta_factors2 = {"cinema": 4}
        social_distance2 = SocialDistancing(
            start_time="2020-03-07", end_time="2020-03-09", beta_factors=beta_factors2
        )
        policies = Policies([social_distance, social_distance2])
        leisure_instance = generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        leisure_instance.distribute_social_venues_to_areas(
            world.areas, super_areas=world.super_areas
        )
        sim.activity_manager.policies = policies
        sim.activity_manager.leisure = leisure_instance
        sim.timer.reset()
        sim.clear_world()
        return sim

    def test__social_distancing_basic(self, social_distancing_sim):
        start_date = datetime(2020, 3, 2)
        end_date = datetime(2020, 3, 5)
        start_date2 = datetime(2020, 3, 7)
        end_date2 = datetime(2020, 3, 9)
        sim = social_distancing_sim
        something_is_checked = False
        while sim.timer.date <= sim.timer.final_date:
            sim.do_timestep()
            if sim.timer.date >= start_date and sim.timer.date < end_date:
                for super_group in sim.world:
                    if super_group.__class__ in [Cities, Cemeteries]:
                        continue
                    for group in super_group:
                        interactive_group = group.get_interactive_group()
                        beta = interactive_group.get_processed_beta(
                            betas=sim.interaction.betas,
                            beta_reductions=sim.interaction.beta_reductions,
                        )
                        if group.spec == "household":
                            assert beta == sim.interaction.betas["household"]
                        else:
                            something_is_checked = True
                            assert (
                                beta
                                == sim.interaction.betas[group.spec]
                                * sim.interaction.beta_reductions[group.spec]
                            )
                next(sim.timer)
                continue
            if sim.timer.date >= start_date2 and sim.timer.date < end_date2:
                for super_group in sim.world:
                    for group in super_group:
                        if super_group.__class__ in [Cities, Cemeteries]:
                            continue
                        interactive_group = group.get_interactive_group()
                        beta = interactive_group.get_processed_beta(
                            betas=sim.interaction.betas,
                            beta_reductions=sim.interaction.beta_reductions,
                        )
                        if group.spec == "cinema":
                            assert beta == 4 * sim.interaction.betas["cinema"]
                        else:
                            assert beta == sim.interaction.betas[group.spec]
                next(sim.timer)
                continue
            next(sim.timer)
        assert something_is_checked

    def test__social_distancing_regional_compliance(self, social_distancing_sim):
        start_date = datetime(2020, 3, 2)
        end_date = datetime(2020, 3, 5)
        start_date2 = datetime(2020, 3, 7)
        end_date2 = datetime(2020, 3, 9)
        sim = social_distancing_sim
        something_is_checked = False
        sim.world.regions[0].regional_compliance = 0.5
        something_is_checked = False
        while sim.timer.date <= sim.timer.final_date:
            sim.do_timestep()
            if sim.timer.date >= start_date and sim.timer.date < end_date:
                for super_group in sim.world:
                    if super_group.__class__ in [Cities, Cemeteries]:
                        continue
                    for group in super_group:
                        interactive_group = group.get_interactive_group()
                        beta = interactive_group.get_processed_beta(
                            betas=sim.interaction.betas,
                            beta_reductions=sim.interaction.beta_reductions,
                        )
                        beta_with_compliance = sim.interaction.betas[group.spec] * (
                            1 + 0.5 * (sim.interaction.beta_reductions[group.spec] - 1)
                        )
                        if group.spec == "household":
                            assert beta == sim.interaction.betas["household"]
                        else:
                            something_is_checked = True
                            assert beta == beta_with_compliance
                next(sim.timer)
                continue
            if sim.timer.date >= start_date2 and sim.timer.date < end_date2:
                for super_group in sim.world:
                    if super_group.__class__ in [Cities, Cemeteries]:
                        continue
                    for group in super_group:
                        interactive_group = group.get_interactive_group()
                        beta = interactive_group.get_processed_beta(
                            betas=sim.interaction.betas,
                            beta_reductions=sim.interaction.beta_reductions,
                        )
                        if group.spec == "cinema":
                            assert beta == sim.interaction.betas["cinema"] * (1 + 0.5 * (4-1))
                        else:
                            assert beta == sim.interaction.betas[group.spec]
                next(sim.timer)
                continue
            next(sim.timer)
        assert something_is_checked


class TestMaskWearing:
    def test__mask_wearing(self, setup_policy_world):
        world, pupil, student, worker, sim = setup_policy_world
        world.cemeteries = Cemeteries()
        start_date = datetime(2020, 3, 10)
        end_date = datetime(2020, 3, 12)
        compliance = 1.0
        beta_factor = 0.5
        mask_probabilities = {
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
        leisure_instance = generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        leisure_instance.distribute_social_venues_to_areas(
            world.areas, super_areas=world.super_areas
        )
        sim.activity_manager.policies = policies
        sim.activity_manager.leisure = leisure_instance
        sim.timer.reset()
        sim.clear_world()
        while sim.timer.date <= sim.timer.final_date:
            sim.do_timestep()
            if sim.timer.date >= start_date and sim.timer.date < end_date:
                for super_group in sim.world:
                    if super_group.__class__ in [Cities, Cemeteries]:
                        continue
                    for group in super_group:
                        interactive_group = group.get_interactive_group()
                        beta = interactive_group.get_processed_beta(
                            betas=sim.interaction.betas,
                            beta_reductions=sim.interaction.beta_reductions,
                        )
                        beta_with_mask = sim.interaction.betas[group.spec] * (
                            1 - (0.5 * 1.0 * (1 - 0.5))                        )
                        if group.spec == "household":
                            assert beta == sim.interaction.betas["household"]
                        else:
                            assert beta == beta_with_mask
                next(sim.timer)
                continue
            else:
                for super_group in sim.world:
                    if super_group.__class__ in [Cities, Cemeteries]:
                        continue
                    for group in super_group:
                        interactive_group = group.get_interactive_group()
                        beta = interactive_group.get_processed_beta(
                            betas=sim.interaction.betas,
                            beta_reductions=sim.interaction.beta_reductions,
                        )
                        assert beta == sim.interaction.betas[group.spec]
            next(sim.timer)
