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
from june.interaction import Interaction
from june.policy import (
    Policy,
    Policies,
    SocialDistancing,
    Hospitalisation,
    InteractionPolicies,
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
            "box": 0.5,
            "pub": 0.5,
            "grocery": 0.5,
            "cinema": 0.5,
            "commute_unit": 0.5,
            "commute_city_unit": 0.5,
            "hospital": 0.5,
            "care_home": 0.5,
            "company": 0.5,
            "school": 0.5,
            "household": 1.0,
            "university": 0.5,
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
        leisure_instance.distribute_social_venues_to_households(world.households)
        sim.activity_manager.policies = policies
        sim.activity_manager.leisure = leisure_instance
        sim.timer.reset()
        initial_betas = copy.deepcopy(sim.interaction.beta)
        sim.clear_world()
        for time in sim.timer:
            if time > sim.timer.final_date:
                break
            sim.do_timestep()
            if sim.timer.date >= start_date and sim.timer.date < end_date:
                for group in sim.interaction.beta:
                    if group != "household":
                        assert sim.interaction.beta[group] == initial_betas[group] * 0.5
                    else:
                        assert sim.interaction.beta[group] == initial_betas[group]
                continue
            if sim.timer.date >= start_date2 and sim.timer.date < end_date2:
                for group in sim.interaction.beta:
                    if group != "cinema":
                        assert sim.interaction.beta == 4.0
                    else:
                        assert sim.interaction.beta[group] == initial_betas[group]
                continue
            assert sim.interaction.beta == initial_betas


