
from june.simulator import Simulator

def test__n_infected(simulator_box):
    n_infections = 50
    simulator_box.seed(simulator_box.world.boxes.members[0],
            n_infections=n_infections)
    assert len(simulator_box.world.people.infected) == n_infections


def test__n_infected(world_ne, interaction, infection_constant):
    simulator = Simulator.from_file(world_ne, interaction, infection_constant,
            config_filename = test_directory / "config_ne.yaml")
    n_infections = 2 
    counter = 0
    household = simulator.world.households.members[counter]
    while household.size < 4:
        counter += 1
        household = simulator.world.households.members[counter]
    simulator.seed(household,
            n_infections=n_infections)

    assert len(household.infected) == n_infections

    for person in simulator.world.people.members:
        if person.health_information.infected:
            print(person.health_information.infected)

    assert len(simulator.world.people.infected) == n_infections




