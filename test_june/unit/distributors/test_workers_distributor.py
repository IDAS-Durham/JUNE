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


default_base_path = Path(os.path.abspath(__file__)).parent.parent.parent.parent
default_workflow_file = default_base_path / \
        "data/processed/flow_in_msoa_wu01ew_2011.csv"
default_sex_per_sector_per_superarea_file = default_base_path / \
        "data/processed/census_data/company_data/companysector_by_sex_cleaned.csv"
default_areas_map_path = default_base_path / \
        "data/processed/geographical_data/oa_msoa_region.csv"
default_config_file = default_base_path / \
        "configs/defaults/distributors/worker_distributor.yaml"

@pytest.fixture(name="config", scope="session")
def load_config():
    with open(default_config_file) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config

@pytest.fixture(name="super_areas", scope="session")
def use_super_areas():
    return ["E02002559", "E02002560", "E02002561"]

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

def test__workers_stay_in_geography(geography, population, super_areas, config):
    case = unittest.TestCase()
    workers_distributor = WorkerDistributor.for_geography(geography)
    workers_distributor.distribute(geography, population)
    work_super_area_name = np.array([
        person.work_super_area.name
        for person in population.people
        if config["age_range"][0] <= person.age <= config["age_range"][1]
    ])
    work_super_area_name = list(np.unique(work_super_area_name))
    case.assertCountEqual(work_super_area_name, super_areas)

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

