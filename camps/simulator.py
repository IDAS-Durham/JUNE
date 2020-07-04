from june.simulator import Simulator
import logging
import random
from typing import List, Optional
import datetime
import copy

from itertools import chain
import numpy as np
import yaml
import time

from june.demography import Person
from june.groups import Group
from june.groups.leisure import Leisure
from june.infection.infection import InfectionSelector
from june.infection import Infection
from june.infection.health_index import HealthIndexGenerator
from june.interaction import Interaction
from june.policy import Policies

from june.logger.logger import Logger
from june.time import Timer
from june.world import World
from june.groups.commute.commuteunit_distributor import CommuteUnitDistributor
from june.groups.commute.commutecityunit_distributor import CommuteCityUnitDistributor
from june.groups.travel.travelunit_distributor import TravelUnitDistributor

from camps import paths

default_config_filename = paths.camp_configs_path / "config_example.yaml"

sim_logger = logging.getLogger(__name__)


class CampSimulator(Simulator):
    def __init__(
        self,
        world: World,
        interaction: Interaction,
        selector: InfectionSelector,
        activity_to_groups: dict,
        time_config: dict,
        infection_seed: Optional["InfectionSeed"] = None,
        leisure: Optional[Leisure] = None,
        min_age_home_alone: int = 15,
        stay_at_home_complacency: float = 0.95,
        policies=Policies(),
        save_path: str = "results",
        output_filename: str = "logger.hdf5",
        light_logger: bool = False,
    ):
        super().__init__(
            world=world,
            interaction=interaction,
            selector=selector,
            activity_to_groups=activity_to_groups,
            time_config=time_config,
            infection_seed=infection_seed,
            leisure=leisure,
            min_age_home_alone=min_age_home_alone,
            policies=policies,
            save_path=save_path,
            output_filename=output_filename,
            light_logger=light_logger,
        )
