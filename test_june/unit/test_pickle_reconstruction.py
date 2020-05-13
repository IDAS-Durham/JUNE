from june.geography import Geography
from june.demography import Demography
from june import World
import pytest


@pytest.fixture(name="original_world", scope="module")
def create_world():
    geography = Geography.from_file({"msoa" : )
