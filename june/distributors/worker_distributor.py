import os
import logging
from pathlib import Path
from itertools import count
from collections import OrderedDict
from typing import List, Tuple, Dict, Optional

import numpy as np
import pandas as pd
from scipy import stats

from june.geography import Geography
from june.demography import Person, Population
from june.infection.health_index import HealthIndex
from june.logger_creation import logger

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

logger = logging.getLogger(__name__)


class WorkerDistributor:
    """
    This class distributes people to their work. Work is understood as the main
    activity any individuum pursues during the week, e.g. for pupils it is
    learning in schools.
    """

    def __init__(
        self,
        workflow_df: pd.DataFrame,
        sector_by_sex_df: pd.DataFrame,
        key_sector_ratio_by_sex_df: pd.DataFrame,
        key_sector_distr_by_sex_df: pd.DataFrame,
    ):
        """
        """
        self.workflow_df = workflow_df
        self.sector_by_sex_df = sector_by_sex_df
        self.key_sector_ratio_by_sex_df = key_sector_ratio_by_sex_df
        self.key_sector_distr_by_sex_df = key_sector_distr_by_sex_df
        self._boundary_workers_counter = count()

    
    def distribute(self, geography: Geography, population: Population):
        self.geography = geography
        for area in iter(geography.areas):  #TODO a.t.m. only for_geography() supported
            wf_area_df = self.workflow_df.loc[(area.super_area.name,)]
            self._work_place_lottery(area.name, wf_area_df, len(area.people))
            for idx, person in enumerate(area.people):
                if working_age_min <= person.age <= working_age_min:
                    self._assign_work_location(idx, person)
                    self._assign_work_sector(idx, person)
        logger.info(f"There are {self.n_boundary_workers} who had to be told to stay real")

    
    def _work_place_lottery(self, area_name, wf_area_df, n_workers):
        """
        """
        # work msoa area/flow data
        work_msoa_man_rv = stats.rv_discrete(
            values=(
                np.arange(0, len(wf_area_df.index.values)),
                wf_area_df["n_man"].values,
            )
        )
        self.work_msoa_man_rnd = work_msoa_man_rv.rvs(size=n_workers)
        work_msoa_woman_rv = stats.rv_discrete(
            values=(
                np.arange(0, len(wf_area_df.index.values)),
                wf_area_df["n_woman"].values,
            )
        )
        self.work_msoa_woman_rnd = work_msoa_woman_rv.rvs(size=n_workers)
        # companies data
        numbers = np.arange(1, 22)
        m_col = [col for col in self.sector_by_sex_df.columns.values if "m " in col]

        distribution_male = self.sector_by_sex_df.loc[area_name][m_col].values
        self.sector_distribution_male = stats.rv_discrete(
            values=(numbers, distribution_male)
        )
        f_col = [col for col in self.sector_by_sex_df.columns.values if "f " in col]
        distribution_female = self.sector_by_sex_df.loc[area_name][f_col].values
        self.sector_distribution_female = stats.rv_discrete(
            values=(numbers, distribution_female)
        )
        self.industry_dict = {
            (idx + 1): col.split(" ")[-1] for idx, col in enumerate(m_col)
        }
        self.sector_male_rnd = self.sector_distribution_male.rvs(size=n_workers)
        self.sector_female_rnd = self.sector_distribution_female.rvs(size=n_workers)

    
    def _assign_work_location(self, i, person):
        """
        """
        if person.sex == "f":
            work_location = self.workflow_df.index.values[self.work_msoa_woman_rnd[i]]
        else:
            work_location = self.workflow_df.index.values[self.work_msoa_man_rnd[i]]
        super_areas = [super_area.name for super_area in self.geography.super_areas]
        idx = np.where(super_areas == work_location)[0]
        if len(idx) != 0:
            self.geography.super_areas.members[idx].add_worker(person)
        else:
            #TODO count people who work outside of the region we currently simulate
            idx = np.random.choice(np.arange(len(self.geography.super_areas)))
            self.geography.super_areas.members[idx].add_worker(person)
            self.n_boundary_workers = next(self._boundary_workers_counter)


    def _assign_work_sector(self, i, person,):
        """
        """
        if person.sex == "f":
            industry_id = self.sector_female_rnd[i]
        else:
            industry_id = self.sector_male_rnd[i]
        person.industry = self.industry_dict[industry_id]

        if person.industry in default_key_compsec_id:
            self._assign_key_industry(person)


    def _assign_key_industry(self, person):
        """
            Healthcares sector
                2211: Medical practitioners
                2217: Medical radiographers
                2231: Nurses
                2232: Midwives

            Education sector
                2311: Higher education teaching professional
                2312: Further education teaching professionals
                2314: Secondary education teaching professionals
                2315: Primary and nursery education teaching professionals
                2316: Special needs education teaching professionals
        """
        # TODO if input date is provided nicely we don't need this anymore
        # TODO this dictionary are the only key_compsec currently implemented
        key_compsec_dict = {
            2314: "secondary",
            2315: "primary",
            2316: "special_needs",
        }
        sector_decoder = {"Q": "healthcare", "P": "education"}
        sex_decoder = {"m": "male", "f": "female"}
        MC_random = np.random.uniform()
        ratio = self.key_sector_ratio_by_sex_df.loc[
            sector_decoder[person.industry], sex_decoder[person.sex]
        ]
        distribution = self.key_sector_distr_by_sex_df.loc[
            (sector_decoder[person.industry],), sex_decoder[person.sex]
        ].values
        # Select people working in key industries
        if MC_random < ratio:
            key_industry_id = None
        else:
            # Assign job category within key industry
            numbers = np.arange(len(distribution))
            random_variable = stats.rv_discrete(values=(numbers, distribution))
            key_industry_id = random_variable.rvs(size=1)
        if key_industry_id is not None:
            key_industry_code = self.key_sector_distr_by_sex_df.loc[
                (sector_decoder[person.industry])
            ].index.values[key_industry_id[0]]
            if key_industry_code in key_compsec_dict.keys():
                person.industry_specific = key_compsec_dict[key_industry_code]
            else:
                person.industry_specific = key_industry_code


    @classmethod
    def for_geography(
            cls,
            geography: Geography,
            workflow_file: str = default_workflow_file,
            sex_per_sector_file: str = default_sex_per_sector_per_superarea_file,
            education_sector_file: str = default_education_sector_file,
            healthcare_sector_file: str = default_healthcare_sector_file,
    ) -> "WorkerDistributor":
        """
        Parameters
        ----------
        geography
            an instance of the geography class
        """
        area_names = [super_area.name for super_area in geography.super_areas]
        if len(area_names) == 0:
            raise CompanyError("Empty geography!")
        return cls.for_super_areas(
            area_names,
            workflow_file,
            sex_per_sector_file,
            education_sector_file,
            healthcare_sector_file,
        )

    
    @classmethod
    def for_zone(
            cls,
            filter_key: Dict[str, list],
            areas_maps_path: str = default_areas_map_path,
            workflow_file: str = default_workflow_file,
            sex_per_sector_file: str = default_sex_per_sector_per_superarea_file,
            education_sector_file: str = default_education_sector_file,
            healthcare_sector_file: str = default_healthcare_sector_file,
    ) -> "WorkerDistributor":
        """
        
        Example
        -------
            filter_key = {"region" : "North East"}
            filter_key = {"msoa" : ["EXXXX", "EYYYY"]}
        """
        if len(filter_key.keys()) > 1:
            raise NotImplementedError("Only one type of area filtering is supported.")
        if "oa" in len(filter_key.keys()):
            raise NotImplementedError("Company data only for the SuperArea (MSOA) and above.")
        geo_hierarchy = pd.read_csv(areas_maps_path)
        zone_type, zone_list = filter_key.popitem()
        area_names = geo_hierarchy[geo_hierarchy[zone_type].isin(zone_list)]["msoa"]
        if len(area_names) == 0:
            raise CompanyError("Region returned empty area list.")
        return cls.for_super_areas(
            area_names,
            workflow_file,
            sex_per_sector_file,
            education_sector_file,
            healthcare_sector_file,
        )

    @classmethod
    def for_super_areas(
            cls,
            area_names: List[str],
            workflow_file: str = default_workflow_file,
            sex_per_sector_file: str = default_sex_per_sector_per_superarea_file,
            education_sector_file: str = default_education_sector_file,
            healthcare_sector_file: str = default_healthcare_sector_file,
    ) -> "WorkerDistributor":
        """
        Parameters
        ----------
        """
        return cls.from_file(
            area_names,
            workflow_file,
            sex_per_sector_file,
            education_sector_file,
            healthcare_sector_file,
        )

    @classmethod
    def from_file(
            cls,
            area_names: Optional[List[str]] = [],
            workflow_file: str = default_workflow_file,
            sex_per_sector_file: str = default_sex_per_sector_per_superarea_file,
            education_sector_file: str = default_education_sector_file,
            healthcare_sector_file: str = default_healthcare_sector_file,
    ) -> "WorkerDistributor":
        workflow_df = _load_workflow_df(
            workflow_file, area_names
        )
        (
            sex_per_sector_df,
            key_sector_ratio_by_sex_df,
            key_sector_distr_by_sex_df,
        ) = _load_sex_per_sector(
            sex_per_sector_file,
            education_sector_file,
            healthcare_sector_file,
            area_names
        )

        return WorkerDistributor(
            workflow_df,
            sex_per_sector_df,
            key_sector_ratio_by_sex_df,
            key_sector_distr_by_sex_df,
        )


def _load_workflow_df(
            workflow_file: str,
            area_names: Optional[List[str]] = []
    ) -> pd.DataFrame:
    wf_df = pd.read_csv(
        workflow_file,
        delimiter=",",
        delim_whitespace=False,
        skiprows=1,
        usecols=[0, 1, 3, 4],
        names=["msoa", "work_msoa", "n_man", "n_woman"],
    )
    if len(area_names) != 0:
        wf_df = wf_df[wf_df["msoa"].isin(area_names)]
    # convert into ratios
    wf_df = wf_df.groupby(["msoa", "work_msoa"]).agg(
        {"n_man": "sum", "n_woman": "sum"}
    )
    wf_df["n_man"] = (
        wf_df.groupby(level=0)["n_man"]
        .apply(lambda x: x / float(x.sum(axis=0)))
        .values
    )
    wf_df["n_woman"] = (
        wf_df.groupby(level=0)["n_woman"]
        .apply(lambda x: x / float(x.sum(axis=0)))
        .values
    )
    return wf_df


def _load_sex_per_sector(
            sector_by_sex_file: str,
            education_sector_file: str,
            healthcare_sector_file: str,
            area_names: Optional[List[str]] = [],
    ) -> pd.DataFrame:
    sector_by_sex_df = pd.read_csv(sector_by_sex_file, index_col=0)
    sector_by_sex_df = sector_by_sex_df.drop(
        ['date', 'geography', 'rural urban'], axis=1,
    )
    sector_by_sex_df = sector_by_sex_df.rename(
        columns={"oareas": "oa"}
    )

    # define all columns in csv file relateing to males
    m_columns = [col for col in sector_by_sex_df.columns.values if "m " in col]
    m_columns.remove('m all')
    m_columns.remove('m R S T U')
    f_columns = [col for col in sector_by_sex_df.columns.values if "f " in col]
    f_columns.remove('f all')
    f_columns.remove('f R S T U')

    uni_columns = [col for col in sector_by_sex_df.columns.values if "all " in col]
    sector_by_sex_df = sector_by_sex_df.drop(
        uni_columns + ['m all', 'm R S T U', 'f all', 'f R S T U'], axis=1,
    )
    
    if len(area_names) != 0:
        geo_hierarchy = pd.read_csv(default_areas_map_path)
        area_names = geo_hierarchy[geo_hierarchy["msoa"].isin(area_names)]["oa"]
        sector_by_sex_df = sector_by_sex_df[
            sector_by_sex_df["oa"].isin(area_names)
        ]
        if (np.sum(sector_by_sex_df["m Q"]) == 0) and \
            (np.sum(sector_by_sex_df["f Q"]) == 0):
            logger.info(f"There exists no Healthcare sector in this geography.")
        if (np.sum(sector_by_sex_df["m P"]) == 0) and \
            (np.sum(sector_by_sex_df["f P"]) == 0):
            logger.info(f"There exists no Education sector in this geography.")
    sector_by_sex_df = sector_by_sex_df.set_index('oa')

    # use the counts to get key company sector ratios
    (
        compsec_specic_ratio_by_sex_df,
        compsec_specic_distr_by_sex_df,
    ) = _read_key_compsec_by_sex(
        sector_by_sex_df,
        education_sector_file,
        healthcare_sector_file,
    )
    
    # convert counts to ratios
    sector_by_sex_df.loc[:, m_columns] = sector_by_sex_df.loc[:, m_columns].div(
        sector_by_sex_df[m_columns].sum(axis=1), axis=0
    )
    sector_by_sex_df.loc[:, f_columns] = sector_by_sex_df.loc[:, f_columns].div(
        sector_by_sex_df[f_columns].sum(axis=1), axis=0
    )
    return (
        sector_by_sex_df,
        compsec_specic_ratio_by_sex_df,
        compsec_specic_distr_by_sex_df
    )

def _read_key_compsec_by_sex(
            sector_by_sex_df: pd.DataFrame,
            education_sector_file: str,
            healthcare_sector_file: str,
    ) -> pd.DataFrame:
    education_df = pd.read_csv(education_sector_file, index_col=0)
    healthcare_df = pd.read_csv(healthcare_sector_file, index_col=0)

    sector_specic_ratio_by_sex_df = _get_key_compsec_ratio_by_sex(
        education_df, healthcare_df, sector_by_sex_df
    )
    sector_specic_distr_by_sex_df = _get_key_compsec_distr_by_sex(
        education_df, healthcare_df
    )
    return sector_specic_ratio_by_sex_df, sector_specic_distr_by_sex_df,

def _get_key_compsec_ratio_by_sex(
            education_df: pd.DataFrame,
            healthcare_df: pd.DataFrame,
            sector_by_sex_df: pd.DataFrame,
    ) -> pd.DataFrame:
    # Get ratio of people work in any compared to the specific key sector
    male_healthcare_ratio = np.sum(healthcare_df["male"]) / \
        np.sum(sector_by_sex_df["m Q"])
    male_education_ratio = np.sum(education_df["male"]) / \
        np.sum(sector_by_sex_df["m P"])
    female_healthcare_ratio = np.sum(healthcare_df["female"]) / \
        np.sum(sector_by_sex_df["f Q"])
    female_education_ratio = np.sum(education_df["female"]) / \
        np.sum(sector_by_sex_df["f P"])

    compsec_specic_ratio_by_sex_df = pd.DataFrame(
        np.array([
            [male_education_ratio, female_education_ratio],
            [male_healthcare_ratio, female_healthcare_ratio]
        ]),
        index=['education', 'healthcare'],
        columns=['male', 'female'],
        dtype=np.float,
    ).replace(np.inf, 5)  # if sector does not exist
    return compsec_specic_ratio_by_sex_df


def _get_key_compsec_distr_by_sex(
            education_df: pd.DataFrame,
            healthcare_df: pd.DataFrame,
    ) -> pd.DataFrame:
    # Get distribution of duties within key sector
    healthcare_distr_df = healthcare_df.loc[
        :,["male", "female"]
    ].div(
        healthcare_df[["male", "female"]].sum(axis=0), axis=1
    )
    #healthcare_distr_df["healthcare_sector"] = healthcare_df.occupations.values
    healthcare_distr_df["healthcare_sector_id"] = healthcare_df.occupation_codes.values
    healthcare_distr_df["sector"] = ["healthcare"] * len(healthcare_distr_df.index.values)
    healthcare_distr_df = healthcare_distr_df.groupby(
        ['sector', 'healthcare_sector_id']
    ).mean()
    
    education_distr_df = education_df.loc[
        :,["male", "female"]
    ].div(
        education_df[["male", "female"]].sum(axis=0), axis=1
    )
    #education_distr_df["education_sector"] = education_df.occupations.values
    education_distr_df["education_sector_id"] = education_df.occupation_codes.values
    education_distr_df["sector"] = ["education"] * len(education_distr_df.index.values)
    education_distr_df = education_distr_df.groupby(
        ['sector', 'education_sector_id']
    ).mean()
    
    compsec_specic_distr_by_sex_df = pd.concat([
        healthcare_distr_df, education_distr_df
    ])
    compsec_specic_distr_by_sex_df = compsec_specic_distr_by_sex_df.sort_index()
 
    return compsec_specic_distr_by_sex_df


if __name__ == '__main__':
    geography = Geography.from_file(filter_key={"region": ["North East"]})
    demography = Demography.for_geography(geography)
    population = demography.populate(geography.areas)
    worker_distr = WorkerDistributor.for_geography(geography)
    worker_distr.distribute(population)
