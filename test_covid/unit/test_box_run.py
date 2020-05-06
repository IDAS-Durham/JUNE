import os
from covid import World


def test__box_run():
    world = World(config_file=os.path.join("../configs", "config_boxmode_example.yaml"),
                 box_mode=True,box_n_people=1000)
    world.group_dynamics(n_seed=100)
    world.logger.plot_infection_curves_per_day()

if __name__ == '__main__':

    test__box_run()
