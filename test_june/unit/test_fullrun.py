"""
This is a quick test that makes sure the box model can be run. It does not check whether it is doing anything correctly,
but at least we can use it in the meantime to make sure the code runs before pusing it to master.
"""

import os

from june import World
from june.infection.health_index import HealthIndexGenerator
from june.interaction import DefaultInteraction 
from june.infection import Infection
from june.infection.symptoms import SymptomsConstant
from june.infection.transmission import TransmissionConstant
from june.simulator import Simulator
from june import World


def test_full_run(simulator):

    seed = Seed(simulator.world.super_areas, simulator.infection, )
    seed.unleash_virus(1000)
    simulator.run()
    simulator.logger.plot_infection_curves_per_day()

