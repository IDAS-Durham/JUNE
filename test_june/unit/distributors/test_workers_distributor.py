import os
import unittest
from pathlib import Path

import numpy as np
import pytest
import yaml

from june.demography import Demography, Population
from june.geography import Geography
from june import paths
from june.distributors import WorkerDistributor, load_workflow_df, load_sex_per_sector

default_config_file = (
    paths.configs_path/ "defaults/distributors/worker_distributor.yaml"
)


@pytest.fixture(name="worker_config", scope="module")
def load_config():
    with open(default_config_file) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


@pytest.fixture(name="worker_super_areas", scope="module")
def use_super_areas():
    return ["E02002559", "E02002560", "E02002561", "E02002665"]  # E00064524


@pytest.fixture(name="worker_geography", scope="module")
def create_geography(worker_super_areas):
    return Geography.from_file(filter_key={"super_area": worker_super_areas})


@pytest.fixture(name="worker_demography", scope="module")
def create_demography(worker_geography):
    return Demography.for_geography(worker_geography)


@pytest.fixture(name="worker_population", scope="module")
def create_population(worker_geography, worker_demography):
    population = list()
    for area in worker_geography.areas:
        area.populate(worker_demography)
        population.extend(area.people)
    distributor = WorkerDistributor.for_geography(worker_geography)
    distributor.distribute(
        areas=worker_geography.areas,
        super_areas=worker_geography.super_areas,
        population=population,
    )
    return population


def test__load_workflow_df(worker_super_areas):
    wf_df = load_workflow_df(area_names=worker_super_areas,)
    assert wf_df["n_man"].sum() == len(worker_super_areas)
    assert wf_df["n_woman"].sum() == len(worker_super_areas)


def test__load_sex_per_sector(worker_super_areas):
    sector_by_sex_df = load_sex_per_sector(area_names=worker_super_areas,)
    m_columns = [col for col in sector_by_sex_df.columns.values if "m " in col]
    f_columns = [col for col in sector_by_sex_df.columns.values if "f " in col]
    m_sum = sector_by_sex_df.loc[:, m_columns].sum(axis="columns").values
    f_sum = sector_by_sex_df.loc[:, f_columns].sum(axis="columns").values
    m_unic_sum = np.sum(np.unique(m_sum))
    f_unic_sum = np.sum(np.unique(f_sum))
    assert m_unic_sum == len(worker_super_areas)
    assert f_unic_sum == len(worker_super_areas)


class TestInitialization:
    def test__distributor_from_file(
        self, worker_super_areas: list,
    ):
        WorkerDistributor.from_file(area_names=worker_super_areas)

    def test__distributor_from_geography(
        self, worker_geography: Geography, worker_population: Population,
    ):
        distributor = WorkerDistributor.for_geography(worker_geography)


class TestDistribution:
    def test__workers_stay_in_geography(
        self,
        worker_config: dict,
        worker_super_areas: list,
        worker_population: Population,
    ):
        case = unittest.TestCase()
        work_super_area_name = np.array(
            [
                person.work_super_area.name
                for person in worker_population
                if (
                    worker_config["age_range"][0]
                    <= person.age
                    <= worker_config["age_range"][1]
                )
                and person.work_super_area is not None
            ]
        )
        work_super_area_name = list(np.unique(work_super_area_name))
        case.assertCountEqual(work_super_area_name, worker_super_areas)

    def test__workers_that_stay_home(
        self, worker_config: dict, worker_population: Population,
    ):
        nr_working_from_home = len(
            [
                person.work_super_area
                for person in worker_population
                if (
                    worker_config["age_range"][0]
                    <= person.age
                    <= worker_config["age_range"][1]
                )
                and person.work_super_area is None 
            ]
        )
        assert 0.050 < nr_working_from_home / len(worker_population) < 0.070

    def test__worker_nr_in_sector_larger_than_its_sub(
        self,
        worker_config: dict,
        worker_population: Population,
    ):
        occupations = np.array(
            [
                [person.sex, person.sector, person.sub_sector]
                for person in worker_population
                if person.sector in list(worker_config["sub_sector_ratio"].keys())
            ]
        ).T
        p_sex = occupations[0]
        p_sectors = occupations[1][p_sex == "m"]
        p_sub_sectors = occupations[2][p_sex == "m"]
        for sector in list(worker_config["sub_sector_ratio"].keys()):
            idx = np.where(p_sectors == sector)[0]
            sector_worker_nr = len(idx)
            p_sub_sector = p_sub_sectors[idx]
            sub_sector_worker_nr = len(p_sub_sector[p_sub_sector != None])

    def test__worker_super_area(self, worker_population, worker_geography):
        has_workers = False
        for super_area in worker_geography.super_areas:
            for worker in super_area.workers:
                has_workers = True
                assert worker.work_super_area == super_area
        assert has_workers
