from pathlib import Path

import pytest

from covid import commute as c

test_file_directory = Path(
    __file__
).parent.parent / "test_data"


@pytest.fixture(
    name="commute_generator"
)
def make_commute_generator():
    return c.CommuteGenerator.from_file(
        test_file_directory / "commute.csv"
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
