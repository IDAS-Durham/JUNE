from june.simulator import Simulator
from pathlib import Path
from june import world
from june.infection import symptoms as sym
from june.infection import infection as infect
from june.infection import transmission as trans
import june.interaction as inter
from june.infection.health_index import HealthIndex

test_directory = Path(__file__).parent.parent.parent

def test__n_infected(simulator_box):
    n_infections = 50
    simulator_box.seed(simulator_box.world.boxes.members[0], n_infections=n_infections)
    assert len(simulator_box.world.people.infected) == n_infections


def test__n_infected():

    reference_health_index = HealthIndex().get_index_for_age(40)
    symptoms = sym.SymptomsConstant(health_index=reference_health_index) 
    transmission = trans.TransmissionConstant(probability=0.3)
    infection = infect.Infection(transmission, symptoms)
    interaction = inter.DefaultInteraction.from_file()
    world_ne = world.World(test_directory / "config_ne.yaml")

    simulator = Simulator.from_file(
        world_ne,
        interaction,
        infection,
        config_filename=test_directory / "config_ne.yaml",
    )
    n_infections = 2
    for household in simulator.world.household.members:
        if household.size > 4:
            break
    simulator.seed(household, n_infections=n_infections)

    assert len(household.infected) == n_infections
    assert len(simulator.world.people.infected) == n_infections
