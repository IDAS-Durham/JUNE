from pathlib import Path

import numpy as np
import pytest

from june import world
from june.demography.person import Person
from june.groups import TestGroup  # this should not be needed anymore
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
def test__time_it_takes_to_infect(config, infection, group_size=2):
    interaction = DefaultInteraction.from_file(test_config_file)

    n_days = []
    for n in range(1000):
        group = TestGroup(1)
        infected_person = Person()
        infection.infect_person_at_time(infected_person, 1)
        group.add(infected_person, qualifier=TestGroup.GroupType.default)
        group[TestGroup.GroupType.default].infected.add(infected_person)
        susceptible_person = Person()
        group.add(susceptible_person, qualifier=TestGroup.GroupType.default)
        for i in range(group_size - 2):
            group.add(Person(), qualifier=TestGroup.GroupType.default)

        # activate everyone in the group
        for person in group.people:
            person.active_group = 'TestGroup'
        n_days.append(
            days_to_infection(interaction, susceptible_person, group)
        )

    np.testing.assert_allclose(
        np.mean(n_days),
        1.0 / (infection.transmission.probability / group_size),
        rtol=0.15,
    )
