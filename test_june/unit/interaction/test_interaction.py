from pathlib import Path

import numpy as np

from june.demography.person import Person
from june.groups import Group 
from june.interaction import DefaultInteraction
from june.infection.infection import InfectionSelector

test_config_file = Path(__file__).parent.parent.parent / "default_interaction.yaml"


def test__set_up_collective_from_file():
    interaction = DefaultInteraction.from_file(test_config_file)
    assert type(interaction).__name__ == "DefaultInteraction"


def days_to_infection(interaction, susceptible_person, group):
    delta_time = 1
    days_to_infection = 0
    while (
        not susceptible_person.health_information.infected and days_to_infection < 100
    ):
        interaction.single_time_step_for_group(group, 1, delta_time)

    days_to_infection += 1
    return days_to_infection

class TestGroup(Group):
    def __init__(self):
        super().__init__()

# @pytest.mark.parametrize(
#    "group_size", (2, 5)

# )
"""        
def test__time_it_takes_to_infect(group_size=2):
    interaction    = DefaultInteraction.from_file(test_config_file)
    interaction.selector = InfectionSelector(transmission_type="Constant",
                                             symptoms_type="Constant")
    n_days = []
    for n in range(1000):
        group = TestGroup()
        infected_person = Person(sex='f', age=26)
        interaction.selector.make_infection(person=infected_person,time=1)
        infection = infected_person.health_information.infection
        group.add(
            infected_person,
            activity_type=infected_person.ActivityType.box,
            subgroup_type=TestGroup.SubgroupType.default,
        )
        group[TestGroup.SubgroupType.default].infected.append(infected_person)
        susceptible_person = Person(sex="m", age=55)
        group.add(
            susceptible_person,
            activity_type=susceptible_person.ActivityType.box,
            subgroup_type=TestGroup.SubgroupType.default,
        )
        for i in range(group_size - 2):
            person = Person()
            group.add(
                person,
                activity_type=person.ActivityType.box,
                subgroup_type=TestGroup.SubgroupType.default,
            )

        n_days.append(
            days_to_infection(interaction, susceptible_person, group)
        )

    np.testing.assert_allclose(
        np.mean(n_days),
        1.0 / (interaction.selector.probability / group_size),
        rtol=0.15,
    )

"""
