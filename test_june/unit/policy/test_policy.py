import copy
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from june import paths
from june.demography import Person, Population
from june.geography import Geography
from june.interaction import Interaction
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
from june.epidemiology.infection import SymptomTag
from june.epidemiology.infection.infection_selector import InfectionSelector
from june.policy import (
    Policy,
    SevereSymptomsStayHome,
    CloseSchools,
    CloseCompanies,
    CloseUniversities,
    Quarantine,
    Shielding,
    Policies,
    SocialDistancing,
    CloseLeisureVenue,
    ChangeLeisureProbability,
    Hospitalisation,
    IndividualPolicies,
    LeisurePolicies,
    InteractionPolicies,
    MedicalCarePolicies,
)
from june.simulator import Simulator
from june.world import World

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
    dir_pwd.parent.parent.parent / "configs/defaults/infection/InfectionXNExp.yaml"
)

@pytest.fixture(name="selector", scope="module")
def create_selector():
    selector = InfectionSelector.from_file(config_filename=constant_config)
    selector.recovery_rate = 0.05
    selector.transmission_probability = 0.7
    return selector


@pytest.fixture(name="interaction", scope="module")
def create_interaction():
    interaction = Interaction.from_file()
    return interaction


@pytest.fixture(name="super_area", scope="module")
def create_geography():
    g = Geography.from_file(filter_key={"super_area": ["E02002559"]})
    return g.super_areas.members[0]

class TestPolicy:
    def test__is_active(self):
        policy = Policy(start_time="2020-5-6", end_time="2020-6-6")
        assert policy.is_active(datetime(2020, 5, 6))
        assert policy.is_active(datetime(2020, 6, 5))
        assert not policy.is_active(datetime(2020, 6, 6))

