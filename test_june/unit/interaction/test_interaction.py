from pathlib import Path

import numpy as np

from june.demography.person import Person
from june.groups import Group 
from june.interaction import DefaultInteraction
from june.infection.infection import InfectionSelector
from june import paths
from pathlib import Path

constant_config = paths.configs_path / "defaults/infection/InfectionConstant.yaml"

test_config_file = paths.configs_path / "tests/default_interaction.yaml"


def test__set_up_collective_from_file():
    interaction = DefaultInteraction.from_file(test_config_file)
    assert type(interaction).__name__ == "DefaultInteraction"


def days_to_infection(interaction, susceptible_person, group):
    delta_time = 1
    days_to_infection = 0
    while (
        not susceptible_person.infected and days_to_infection < 100
    ):
        interaction.single_time_step_for_group(group, days_to_infection, delta_time, logger=None)
        days_to_infection += 1

    return days_to_infection

class TestGroup(Group):
    def __init__(self):
        super().__init__()

# @pytest.mark.parametrize(
#    "group_size", (2, 5)

# )
def test__time_it_takes_to_infect(group_size=2):
    selector = InfectionSelector.from_file(constant_config)
    interaction    = DefaultInteraction.from_file(test_config_file, selector)
    n_days = []
    for n in range(1_000):
        group = TestGroup()
        infected_person = Person.from_attributes(sex='m', age=75)
        selector.infect_person_at_time(infected_person,time=0)
        group.add(
            infected_person,
            activity="box",
            subgroup_type=TestGroup.SubgroupType.default,
        )
        group[TestGroup.SubgroupType.default].infected.append(infected_person)
        susceptible_person = Person.from_attributes(sex="m", age=55)
        group.add(
            susceptible_person,
            activity="box",
            subgroup_type=TestGroup.SubgroupType.default,
        )
        for i in range(group_size - 2):
            person = Person()
            group.add(
                person,
                activity="box",
                subgroup_type=TestGroup.SubgroupType.default,
            )

        n_days.append(
            days_to_infection(interaction, susceptible_person, group)
        )

    np.testing.assert_allclose(
        np.mean(n_days),
        1.0 / (interaction.selector.transmission_probability / group_size),
        rtol=0.15,
    )
