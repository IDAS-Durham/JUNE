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


@pytest.fixture(
    name="regional_generator"
)
def make_regional_generator(
        commute_generator
):
    return commute_generator.regional_generators[0]


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
        regional_generator
):
    assert regional_generator.code == "E00062207"


def test_weighted_modes(regional_generator):
    weighted_modes = regional_generator.weighted_modes
    assert len(regional_generator.weighted_modes) == 12

    weighted_mode = weighted_modes[0]
    assert weighted_mode[0] == 15
    assert weighted_mode[1] == "Work mainly at or from home"


def test_weights(regional_generator):
    assert regional_generator.total == 180

    weights = regional_generator.weights
    assert len(weights) == 12
    assert sum(weights) == pytest.approx(1.0)


def test_weighted_random_choice(regional_generator):
    result = regional_generator.weighted_random_choice()
    assert isinstance(result, c.ModeOfTransport)


def test_modes_of_transport():
    modes_of_transport = c.ModeOfTransport.load_from_file()
    assert len(modes_of_transport) == 12
    assert "Work mainly at or from home" in modes_of_transport
    assert c.ModeOfTransport.load_from_file()[0] is modes_of_transport[0]
