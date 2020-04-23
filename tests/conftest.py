from covid import World
import pytest

@pytest.fixture(name="world_ne", scope="session")
def create_world_northeast():
    world = World("config_ne.yaml")
    return world
