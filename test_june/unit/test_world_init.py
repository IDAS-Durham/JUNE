from os import path
import logging
import pytest

from june import World


@pytest.fixture(name="world")
def make_create_world_init():
    world = World(
        configs_dir = "../example_config_dir/",
        output_dir = "../example_output_dir/",
    )
    return world


class TestRealWorld:
    def test__logger(self, world):
        world.logger(config_file = world.configs_dir + "example_file.yaml")
        logger = logging.getLogger(__name__)
        assert logger


    def test__essential_inputs(self, world):
        assert hasattr(world.inputs, 'area_mapping_file')
        assert hasattr(world.inputs, 'n_residents_file')


    def test__box(self, world):
        assert world.box == None


class TestBoxWorld:
    def test__world_box_mode(self):
        world = World(
            configs_dir = "../example_config_dir/",
            output_dir = "../example_output_dir/",
            box_mode = {"n_people": 10, "zone": "Trisolaris"}
        )
        assert type(world.box) is dict
        assert type(world.box["n_people"]) is int
        assert type(world.box["zone"]) is str
