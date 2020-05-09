"""
This is a quick test that makes sure the box model can be run. It does not check whether it is doing anything correctly,
but at least we can use it in the meantime to make sure the code runs before pusing it to master.
"""

import os

from covid import World
from covid.groups.people.health_index import HealthIndex
from covid.interaction import DefaultInteraction 
from covid.infection import Infection
from covid.infection.symptoms import SymptomsConstant
from covid.infection.transmission import TransmissionConstant
from covid.simulator import Simulator



def test_full_run(world_ne):
    world_ne.group_dynamics()


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    config_path = os.path.join(
            os.path.dirname(
                os.path.realpath(__file__)
            ),
            "..",
            "config_ne.yaml"
    )
    world = World(config_path, box_mode=False)

    reference_health_index = HealthIndex().get_index_for_age(40)
    symptoms = SymptomsConstant(health_index=reference_health_index, recovery_rate=0.05)
    transmission = TransmissionConstant(probability=0.3) 
    infection = Infection(transmission, symptoms)
    interaction = DefaultInteraction()


    simulator = Simulator.from_file(world, interaction, infection, config_filename = config_path)
    for household in simulator.world.households.members[:20]:
        simulator.seed(household, n_infections=1)
    simulator.run()
    simulator.logger.plot_infection_curves_per_day()
    plt.show()


