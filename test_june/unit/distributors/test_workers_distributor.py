import os
import unittest
from pathlib import Path

import numpy as np
import pytest
import yaml

from june.demography import Demography, Population
from june.distributors import WorkerDistributor
from june.geography import Geography

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
    return ["E02002559", "E02002560", "E02002561", "E02002665"] # E00064524


@pytest.fixture(name="worker_geography", scope="module")
def create_geography(worker_super_areas):
    return Geography.from_file(filter_key={"msoa": worker_super_areas})


@pytest.fixture(name="worker_demography", scope="module")
def create_demography(worker_geography):
    return Demography.for_geography(worker_geography)


@pytest.fixture(name="worker_population", scope="module")
def create_population(worker_geography, worker_demography):
    population = list()
    for area in worker_geography.areas:
        area.populate(worker_demography)
        population.extend(
            area.people
        )
    distributor = WorkerDistributor.for_geography(worker_geography)
    distributor.distribute(worker_geography, population)
    return population


class TestInitialization:
    def test__distributor_from_file(
            self,
            worker_super_areas: list,
    ):
        WorkerDistributor.from_file(area_names = worker_super_areas)
    

    def test__distributor_from_geography(
            self,
            worker_geography: Geography,
            worker_population: Population,
    ):
        distributor = WorkerDistributor.for_geography(worker_geography)


class TestDistribution:
    def test__workers_stay_in_geography(
            self,
            worker_config: dict,
            worker_super_areas: list,
            worker_geography: Geography,
            worker_population: Population,
    ):
        case = unittest.TestCase()
        work_super_area_name = np.array([
            person.work_super_area.name
            for person in worker_population
            if (
                worker_config["age_range"][0] <= person.age <= worker_config["age_range"][1]
                ) and not isinstance(person.work_super_area, str)

        ])
        work_super_area_name = list(np.unique(work_super_area_name))
        case.assertCountEqual(work_super_area_name, worker_super_areas)

    def test__worker_nr_in_sector_larger_than_its_sub(
           self,
           worker_config: dict,
           worker_geography: Geography,
           worker_population: Population,
    ):
       occupations = np.array([
           [person.sex, person.sector, person.sub_sector]
           for person in worker_population
           if person.sector in list(worker_config["sub_sector_ratio"].keys())
       ]).T
       p_sex = occupations[0]
       p_sectors = occupations[1][p_sex == "m"]
       p_sub_sectors = occupations[2][p_sex == "m"]
       for sector in list(worker_config["sub_sector_ratio"].keys()):
           idx = np.where(p_sectors == sector)[0]
           sector_worker_nr = len(idx)
           p_sub_sector = p_sub_sectors[idx]
           sub_sector_worker_nr = len(p_sub_sector[p_sub_sector != None])
           print("------>", sector_worker_nr, sub_sector_worker_nr) 
