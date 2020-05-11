import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from june.geography import Geography
from june.demography import Demography
from june.demography import Person, Population
from june.distributors import WorkerDistributor


default_data_path = Path(os.path.abspath(__file__)).parent.parent.parent / "data/"
default_workflow_file = default_data_path / \
        "processed/flow_in_msoa_wu01ew_2011.csv"
default_sex_per_sector_per_superarea_file = default_data_path / \
        "processed/census_data/company_data/companysector_by_sex_cleaned.csv"
default_education_sector_file = default_data_path / \
        "processed/census_data/company_data/education_by_sex_2011.csv"
default_healthcare_sector_file = default_data_path / \
        "processed/census_data/company_data/healthcare_by_sex_2011.csv"
default_areas_map_path = default_data_path / \
        "processed/geographical_data/oa_msoa_region.csv"
#TODO put in config
working_age_min = 18
working_age_min = 65
default_key_compsec_id = ["P", "Q"]

@pytest.fixture(name="geography_workers", scope="module")
def create_geography():
    return Geography.from_file(filter_key={"msoa" : ["E02002559", "E02002560", "E02002561"]})


@pytest.fixture(name="population_workers", scope="module")
def create_population(geography_workers):
    demography = Demography.for_geography(geography_workers)
    return demography.populate(geography_workers.areas)


def test__workers_distribution_for_geography(geography_workers, population_workers):
    workers_distributor = WorkerDistributor.for_geography(geography_workers)
    return workers_distributor.distribute(geography_workers, population_workers)
