import pytest

from june.geography import Geography
from june.groups.leisure import Pubs


@pytest.fixture(name="geography")
def make_geography():
    geography = Geography.from_file({"super_area": ["E02005103"]})
    return geography


class TestPubs:
    def test__create_pubs_in_geography(self, geography):
        pubs = Pubs.for_geography(geography)
        assert len(pubs) == 257
        return pubs
