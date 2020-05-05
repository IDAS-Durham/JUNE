from covid.interaction import interaction as inter
from pathlib import Path
from covid.groups import *
import numpy as np
import pytest

test_config_file = Path(__file__).parent.parent.parent / "interaction_collective.yaml"


def test__set_up_collective_from_file():
    interaction = inter.InteractionCollective.from_file(test_config_file)
    assert type(interaction).__name__ == "InteractionCollective"


def days_to_infection(interaction, susceptible_person, group, timer):
    delta_time = 1
    days_to_infection = 0

    while (
        susceptible_person.health_information.infected == False
        and days_to_infection < 100
    ):
        effective_load = interaction.calculate_effective_viral_load(group, delta_time,)

        interaction.single_time_step_for_recipient(
            susceptible_person, effective_load, group, timer.now
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
def test__time_it_takes_to_infect(interaction_type, group_size, world_ne):
    interaction = inter.InteractionCollective(
        mode=interaction_type, intensities={"TestGroup": 1.0}
    )
    infected_reference = world_ne.initialize_infection()

    n_days = []
    for n in range(1000):
        group = TestGroup(1)
        infected_person = Person(world_ne)
        infected_reference.infect_person_at_time(infected_person, world_ne.timer.now)
        group.people.append(infected_person)
        for i in range(group_size - 1):
            susceptible_person = Person(world_ne)
            group.people.append(susceptible_person)
        n_days.append(
            days_to_infection(interaction, susceptible_person, group, world_ne.timer)
        )

    np.testing.assert_allclose(
        np.mean(n_days),
        1.0 / (infected_reference.transmission.probability / group_size),
        rtol=0.1,
    )
