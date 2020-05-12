import os
import yaml
from pathlib import Path

import numpy as np
import numpy.testing as npt
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


@pytest.fixture(name="worker_config", scope="module")
def load_config():
    with open(default_config_file) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


@pytest.fixture(name="worker_super_areas", scope="module")
def use_super_areas():
    return ["E02002559", "E02002560", "E02002561"]


@pytest.fixture(name="worker_geography", scope="module")
def create_geography(worker_super_areas):
    return Geography.from_file(filter_key={"msoa" : worker_super_areas})


@pytest.fixture(name="worker_population", scope="module")
def test__worker_population(worker_geography):
    demography = Demography.for_geography(worker_geography)
    population = demography.populate(worker_geography.areas)
    distributor = WorkerDistributor.for_geography(worker_geography)
    distributor.distribute(worker_geography, population)
    return population


class TestDistributor():
    def test__workers_stay_in_geography(
            self,
            worker_geography,
            worker_population,
            worker_super_areas,
            worker_config
    ):
        case = unittest.TestCase()
        work_super_area_name = np.array([
            person.work_super_area.name
            for person in worker_population.people
            if worker_config["age_range"][0] <= person.age <= worker_config["age_range"][1]
        ])
        work_super_area_name = list(np.unique(work_super_area_name))
        case.assertCountEqual(work_super_area_name, worker_super_areas)


    #def test__sex_ratio_in_geography(
    #        self,
    #        worker_geography,
    #        worker_population,
    #        worker_config
    #):
    #    occupations = np.array([
    #        [person.sex, person.sector, person.sub_sector]
    #        for person in worker_population.people
    #        if person.sector in list(worker_config["sub_sector_ratio"].keys())
    #    ]).T
    #    p_sex = occupations[0]
    #    p_sectors = occupations[1][p_sex == "m"]
    #    p_sub_sectors = occupations[2][p_sex == "m"]
    #    for sector in list(worker_config["sub_sector_ratio"].keys()):
    #        idx = np.where(p_sectors == sector)[0]
    #        sector_worker_nr = len(idx)
    #        p_sub_sector = p_sub_sectors[idx]
    #        sub_sector_worker_nr = len(np.where(p_sub_sector is not None)[0])
    #        if not sub_sector_worker_nr == 0:
    #            npt.assert_almost_equal(
    #                sector_worker_nr / sub_sector_worker_nr, 
    #                worker_config["sub_sector_ratio"][sector]["m"],
    #                decimal=3,
    #            )


