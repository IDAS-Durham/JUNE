from pathlib import Path

import numpy as np
import pytest

from june import world
from june.groups.people import Person
from june.groups.test_groups import TestGroup
from june.interaction import *

test_config_file = Path(__file__).parent.parent.parent / "default_interaction.yaml"


def test__set_up_collective_from_file():
    interaction = DefaultInteraction.from_file(test_config_file)
    assert type(interaction).__name__ == "DefaultInteraction"


def days_to_infection(interaction, susceptible_person, group):
    delta_time = 1
    days_to_infection = 0

    while (
            not susceptible_person.health_information.infected
            and days_to_infection < 100
    ):
        interaction.single_time_step_for_group(
            group, 1, delta_time
        )

        days_to_infection += 1
    return days_to_infection


#@pytest.mark.parametrize(
#    "group_size", (2, 5)
#)
def test__time_it_takes_to_infect(config, group_size=2):
    interaction = DefaultInteraction.from_file(test_config_file)

    infected_reference = world._initialize_infection(
        config,
        1
    )

    n_days = []
    for n in range(1000):
        group = TestGroup(1)
        infected_person = Person()
        infected_reference.infect_person_at_time(infected_person, 1)
        group.add(infected_person, qualifier=TestGroup.GroupType.default)
        group[TestGroup.GroupType.default].infected.add(infected_person)
        susceptible_person = Person()
        group.add(susceptible_person, qualifier=TestGroup.GroupType.default)
        for i in range(group_size - 2):
            group.add(Person(), qualifier=TestGroup.GroupType.default)

        n_days.append(
            days_to_infection(interaction, susceptible_person, group)
        )

    np.testing.assert_allclose(
        np.mean(n_days),
        1.0 / (infected_reference.transmission.probability / group_size),
        rtol=0.1,
    )
