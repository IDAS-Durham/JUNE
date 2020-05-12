import os
import yaml
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import unittest

from june.geography import Geography
from june.demography import Demography
from june.demography import Person, Population
from june.distributors import WorkerDistributor



@pytest.fixture(name="geography", scope="session")
def create_geography(super_areas):
    return Geography.from_file(filter_key={"msoa" : super_areas})


@pytest.fixture(name="population", scope="session")
def create_population(geography):
    demography = Demography.for_geography(geography)
    return demography.populate(geography.areas)


def test__workers_distribution_for_geography(geography, population):
    workers_distributor = WorkerDistributor.for_geography(geography)
    return workers_distributor.distribute(geography, population)

# work in progress:
#def test__sub_sector_ratio_for_geography(geography, population):
#    workers_distributor = WorkerDistributor.for_geography(geography)
#    workers_distributor.distribute(geography, population)
#    sex, sector, sub_sector = np.array([
#        [person.sex, person.sector, person.sub_sector]
#        for person in population.people
#    ]).T
#    idx = np.where(sector == "P")[0]
#    print(idx)
#    ratio




