from pathlib import Path

import pytest

from covid import commute as c

data_filename = Path(
    __file__
).parent.parent / "test_data/commute.csv"


@pytest.fixture(
    name="commute_generator"
)
def make_commute_generator():
    return c.CommuteGenerator.from_file(
        data_filename
    )


def test_load(
        commute_generator
):
    assert isinstance(
        commute_generator,
        c.CommuteGenerator
    )

    regional_generators = commute_generator.regional_generators
    assert len(regional_generators) == 8802


def test_regional_generators(
        commute_generator
):
    regional_generator = commute_generator.regional_generators[0]
    assert regional_generator.code == "E00062207"

    weighted_modes = regional_generator.weighted_modes
    assert len(regional_generator.weighted_modes) == 12

    weighted_mode = weighted_modes[0]
    assert weighted_mode[0] == 15
    assert weighted_mode[1] == "Work mainly at or from home"


def test_modes_of_transport():
    modes_of_transport = c.ModeOfTransport.load_from_file()
    assert len(modes_of_transport) == 12
    assert "Work mainly at or from home" in modes_of_transport
    assert c.ModeOfTransport.load_from_file()[0] is modes_of_transport[0]
