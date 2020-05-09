import autofit as af
import pytest
import os

from june import world_new as w

# TODO : move to test_world.py when world is ready.

directory = os.path.dirname(os.path.realpath(__file__))

@pytest.fixture(scope="session", autouse=True)
def do_something():
    af.conf.instance = af.conf.Config(config_path="{}/files/config/".format(directory))

class TestEpidemiology:

    def test__if_not_passed_to_init_loads_using_config_values(self):

        world = w.World(epidemiology=None)

        assert world.e