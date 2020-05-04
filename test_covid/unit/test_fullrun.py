"""
This is a quick test that makes sure the box model can be run. It does not check whether it is doing anything correctly,
but at least we can use it in the meantime to make sure the code runs before pusing it to master.
"""

import os

from covid import World


def test_full_run():
    world = World(
        os.path.join(
            os.path.dirname(
                os.path.realpath(__file__)
            ),
            "../..",
            "configs",
            "config_example.yaml"
        ),
        box_mode=False
    )
    world.group_dynamics()


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
    world.group_dynamics()
    world.logger.plot_infection_curves_per_day()
    plt.show()
