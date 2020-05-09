


def test__n_infected(simulator_box):
    n_infections = 50
    simulator_box.seed(simulator_box.world.boxes.members[0],
            n_infections=n_infections)
    assert len(simulator_box.world.people.infected) == n_infections


def test__n_infected(simulator):
    n_infections = 2 
    simulator.seed(simulator.world.schools.members[0],
            n_infections=n_infections)
    assert len(simulator.world.people.infected) == n_infections




