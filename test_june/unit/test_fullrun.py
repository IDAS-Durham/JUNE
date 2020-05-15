"""
This is a quick test that makes sure the box model can be run. It does not check whether it is doing anything correctly,
but at least we can use it in the meantime to make sure the code runs before pusing it to master.
"""

from june.seed import Seed


def test_full_run(simulator):

    seed = Seed(simulator.world.super_areas, simulator.infection, )
    seed.unleash_virus(100)
    simulator.run()
    simulator.logger.plot_infection_curves_per_day()
