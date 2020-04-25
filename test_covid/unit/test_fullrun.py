"""
This is a quick test that makes sure the box model can be run. It does not check whether it is doing anything correctly,
but at least we can use it in the meantime to make sure the code runs before pusing it to master.
"""

from covid import World
import os

def test_full_run():
    world = World(os.path.join("..", "configs", "config_example.yaml"), box_mode=False)
    world.group_dynamics()

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    world = World(os.path.join("..", "configs", "config_example.yaml"), box_mode=False)
    world.group_dynamics()
    world.logger.plot_infection_curves_per_day()
    plt.show()




