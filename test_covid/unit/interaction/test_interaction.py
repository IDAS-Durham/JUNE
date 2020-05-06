from covid.interaction import interaction as inter
from pathlib import Path
from covid.groups import *
import numpy as np
import pytest
from covid import world

test_config_file = Path(__file__).parent.parent.parent / "interaction_collective.yaml"


def test__set_up_collective_from_file():
    interaction = inter.InteractionCollective.from_file(test_config_file)
    assert type(interaction).__name__ == "InteractionCollective"


def days_to_infection(interaction, susceptible_person, group):
    delta_time = 1
    days_to_infection = 0
    group.update_status_lists(
        days_to_infection,
        delta_time
    )

    while (
        not susceptible_person.health_information.infected
        and days_to_infection < 100
    ):
        effective_load = interaction.calculate_effective_viral_load(group, delta_time,)

        interaction.single_time_step_for_recipient(
            susceptible_person, effective_load, group, 1
        )

        days_to_infection += 1
    return days_to_infection


@pytest.mark.parametrize(
    "interaction_type, group_size",
    [
        ("probabilistic", 2),
        ("superposition", 2),
        ("probabilistic", 5),
        ("superposition", 5),
    ],
)
def test__time_it_takes_to_infect(interaction_type, group_size, config):
    interaction = inter.InteractionCollective(
        mode=interaction_type, intensities={"TestGroup": 1.0}
    )

    infected_reference = world._initialize_infection(
        config,
        1
    )

    n_days = []
    for n in range(1000):
        group = TestGroup(1)
        infected_person = Person()
        infected_reference.infect_person_at_time(infected_person, 1)
        group.people.add(infected_person)
        susceptible_person = Person()
        group.people.add(susceptible_person)
        for i in range(group_size - 2):
            group.people.add(Person())
        n_days.append(
            days_to_infection(interaction, susceptible_person, group)
        )

    np.testing.assert_allclose(
        np.mean(n_days),
        1.0 / (infected_reference.transmission.probability / group_size),
        rtol=0.1,
    )
