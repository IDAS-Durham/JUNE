from pathlib import Path

from covid import commute as c

test_file_directory = Path(
    __file__
).parent.parent / "test_data"


def test_load():
    commute_generator = c.CommuteGenerator.from_file(
        test_file_directory / "commute.csv"
    )
    assert isinstance(
        commute_generator,
        c.CommuteGenerator
    )
    assert len(commute_generator.regional_generators) == 105
