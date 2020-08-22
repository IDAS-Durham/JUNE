import os
from pathlib import Path

import numpy as np
import random
import pandas as pd
import pytest

from june.time import Timer
from june.demography.geography import Geography, SuperArea, Area
from june.demography import Demography, Person
from june.groups.leisure import Pub, Pubs, supergroup_factory


@pytest.fixture(name="geography")
def make_geography():
    geography = Geography.from_file({"super_area": ["E02005103"]})
    return geography


class TestPubs:
    def test__create_pubs_in_geography(self, geography):
        pubs = Pubs.for_geography(geography)
        assert len(pubs) == 7
        return pubs

    def test__create_pubs_dynamically_for_geography(self, geography):
        DynPubs,DynPub = supergroup_factory("pubs", "pub", return_group=True)
        pubs2 = DynPubs.for_geography(geography)
        assert len(pubs2) == 7
        return pubs2
