import pytest
import numpy.testing as npt

from june import geography as g


@pytest.fixture(name="geography")
def create_geography():
    return g.Geography.from_file(
        filter_key={"MSOA": ["E02000140"]}
    )


def test__nr_of_members_in_units(geography):
    assert len(geography.areas) == 178
    assert len(geography.super_areas) == 1

def test__area_attributes(geography):
    area = geography.areas.members[0]
    assert area.id == 0
    assert area.name == "E00003598"
    npt.assert_almost_equal(
        area.coordinate,
        [51.395954503652504, 0.10846483370388499],
        decimal=3,
    )
    assert area.super_area.name in "E02000140"

def test__super_area_attributes(geography):
    super_area = geography.super_areas.members[0]
    assert super_area.id == 0
    assert super_area.name == "E02000140"
    npt.assert_almost_equal(
        super_area.coordinate,
        [51.40340615262757, 0.10741193961090514],
        decimal=3,
    )
    assert "E00003595" in [area.name for area in super_area.areas]
