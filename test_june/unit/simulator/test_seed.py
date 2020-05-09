from june.simulator import Simulator
from pathlib import Path
from june import world

test_directory = Path(__file__).parent.parent.parent

def test__n_infected(simulator_box):
    n_infections = 50
    simulator_box.seed(simulator_box.world.boxes.members[0], n_infections=n_infections)
    assert len(simulator_box.world.people.infected) == n_infections


def test__n_infected(interaction, infection_constant):

    world_ne = world.World(test_directory / "config_ne.yaml")
    simulator = Simulator.from_file(
        world_ne,
        interaction,
        infection_constant,
        config_filename=test_directory / "config_ne.yaml",
    )
    n_infections = 2
    counter = 0
    household = simulator.world.households.members[counter]
    while household.size < 4:
        counter += 1
        household = simulator.world.households.members[counter]
    simulator.seed(household, n_infections=n_infections)

    assert len(household.infected) == n_infections
    assert len(simulator.world.people.infected) == n_infections
