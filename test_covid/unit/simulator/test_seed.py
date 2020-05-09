


def test__n_infected(simulator_box):
    n_infections = 50
    simulator_box.seed(simulator_box.world.boxes.members[0],
            n_infections=n_infections)
    assert len(simulator_box.world.people.infected) == n_infections

