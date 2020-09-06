"""
This is a quick test that makes sure the box model can be run. It does not check whether it is doing anything correctly,
but at least we can use it in the meantime to make sure the code runs before pusing it to master.
"""

from june.infection_seed import InfectionSeed
from june.demography import Population


def test_box_full_run(simulator_box, selector):
    seed = InfectionSeed(simulator_box.world.boxes, selector, )
    seed.unleash_virus(Population(simulator_box.world.people), 10, box_mode=True)
    simulator_box.run()
