import os
import logging
from enum import IntEnum
from pathlib import Path
from itertools import count
from typing import List, Tuple, Dict, Optional

import numpy as np
import pandas as pd
from scipy.stats import rv_discrete

from june.geography import Geography
from june.groups.group import Group
from june.logger_creation import logger

default_data_path = Path(os.path.abspath(__file__)).parent.parent.parent / \
    "data/processed/census_data/company_data/"
default_size_nr_file = default_data_path / "companysize_msoa11cd_2019.csv"
default_sector_nr_per_msoa_file = default_data_path / "companysector_msoa11cd_2011.csv"
default_areas_map_path = Path(os.path.abspath(__file__)).parent.parent.parent / \
    "data/processed/geographical_data/oa_msoa_region.csv"

logger = logging.getLogger(__name__)


class CompanyError(BaseException):
    pass


class Company(Group):
    """
    The Company class represents a company that contains information about 
    its workers which are not yet distributed to key company sectors
    (e.g. as schools and hospitals).

    Currently we treat the workforce of a company as one single sub-group
    and therefore we invoke the base class group with the default Ngroups = 1.
    We made this explicit here, although it is not necessary.
    """

    _id = count()
    __slots__ = "id", "super_area", "n_woman", "employees", "industry"

    class GroupType(IntEnum):
        workers = 0

    def __init__(self, super_area=None, n_employees_max=int, industry=None):
        self.id = next(self._id)
        super().__init__(name=f"Company_{self.id}", spec="company")
        self.super_area = super_area
        # set the max number of employees to be the mean number in a range
        self.n_woman = 0
        self.employees = []
        self.industry = industry

    def add(self, person, qualifier=GroupType.workers):
        super().add(person, qualifier)
        person.company = self


class Companies:
    def __init__(self, companies: List["Companies"]):
        """
        Create companies and provide functionality to allocate workers.

        Parameters
        ----------
        company_size_per_superarea_df: pd.DataFram
            Nr. of companies within a size-range per SuperArea.

        compsec_per_msoa_df: pd.DataFrame
            Nr. of companies per industry sector per SuperArea.
        """
        self.members = companies

    @classmethod
    def for_geography(
            cls,
            geography: Geography,
            size_nr_file: str = default_size_nr_file,
            sector_nr_per_msoa_file: str = default_sector_nr_per_msoa_file,
    ) -> "Companies":
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
            size_nr_file,
            sector_nr_per_msoa_file
        )

    @classmethod
    def for_zone(
            cls,
            filter_key: Dict[str, list],
            areas_maps_path: str = default_areas_map_path,
            size_nr_file: str = default_size_nr_file,
            sector_nr_per_msoa_file: str = default_sector_nr_per_msoa_file,
    ) -> "Companies":
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
        return cls.for_super_areas(area_names, size_nr_file, sector_nr_per_msoa_file)

    @classmethod
    def for_super_areas(
            cls,
            area_names: List[str],
            size_nr_file: str = default_size_nr_file,
            sector_nr_per_msoa_file: str = default_sector_nr_per_msoa_file,
    ) -> "Companies":
        """
        Parameters
        ----------
        """
        return cls.from_file(area_names, size_nr_file, sector_nr_per_msoa_file)
    
    @classmethod
    def from_file(
            cls,
            area_names: Optional[List[str]] = [],
            size_nr_file: str = default_size_nr_file,
            sector_nr_per_superarea_file: str = default_sector_nr_per_msoa_file,
    ) -> "Companies":
        """
        Parameters
        ----------
        """
        # converting nr of companies in size-range-bin into fractions of the
        # total nr. of companies
        size_per_superarea_df = pd.read_csv(size_nr_file, index_col=0)
        size_per_superarea_df = size_per_superarea_df.div(
            size_per_superarea_df.sum(axis=1), axis=0
        )
        size_per_superarea_df = size_per_superarea_df.reset_index(
        ).rename(columns={"MSOA": "superarea"})
        # read nr of companies in each industry sector per super_area
        sector_per_superarea_df = pd.read_csv(
            sector_nr_per_superarea_file#, index_col=0
        )
        sector_per_superarea_df = sector_per_superarea_df.rename(
            columns={"MSOA": "superarea"}
        )
        return cls.from_df(
            size_per_superarea_df,
            sector_per_superarea_df,
            area_names,
        )

    @classmethod
    def from_df(
            cls,
            size_per_superarea_df: pd.DataFrame,
            sector_per_superarea_df: pd.DataFrame,
            area_names: Optional[List[str]] = [],
    ) -> "Companies":
        """
        Initializes Companies class from a list of companies read from a DataFrame.

        Parameters
        ----------
        companysize_file
            Pandas dataframe with number of companies within a size-range per SuperArea.
        company_per_sector_per_msoa_file
            Pandas dataframe with number of companies per industry sector per SuperArea.
        """
        if len(area_names) is not 0:
            # filter out schools that are in the area of interest
            size_per_superarea_df = size_per_superarea_df[
                size_per_superarea_df["superarea"].isin(area_names)
            ]
            sector_per_superarea_df = sector_per_superarea_df[
                sector_per_superarea_df["superarea"].isin(area_names)
            ]
        size_per_superarea_df = size_per_superarea_df.set_index('superarea')
        sector_per_superarea_df = sector_per_superarea_df.set_index('superarea')
        return cls.build_companies_for_super_areas(
            size_per_superarea_df,
            sector_per_superarea_df,
        )

    @classmethod
    def build_companies_for_super_areas(
            cls,
            size_per_superarea_df: pd.DataFrame,
            sector_per_superarea_df: pd.DataFrame,
    ) -> "Companies":
        compsize_labels = size_per_superarea_df.columns.values
        compsize_labels_encoded = np.arange(1, len(compsize_labels) + 1)
        companysize_data_per_area = size_per_superarea_df.values
        company_per_sector_data_per_area = sector_per_superarea_df.values
        size_dict = {
            (idx + 1): _compute_size_mean(size_label)
            for idx, size_label in enumerate(compsize_labels)
        }
        super_area_names = size_per_superarea_df.index.values
        # Run through each SuperArea
        compsec_labels = sector_per_superarea_df.columns
        
        companies = []
        for area_counter, (company_sizes, company_sectors) in enumerate(
            zip(companysize_data_per_area, company_per_sector_data_per_area)
        ):
            comp_size_rv = rv_discrete(values=(compsize_labels_encoded, company_sizes))
            comp_size_rnd_array = comp_size_rv.rvs(
                size=np.sum(company_sectors).astype(int)
            )
            # Run through each industry sector
            for i, nr_of_comp in enumerate(company_sectors):
                label = compsec_labels[i]
                # Run through all companies within sector within SuperArea
                for i in range(int(nr_of_comp)):
                    company = Company(
                        super_area=super_area_names[area_counter],
                        n_employees_max=size_dict[comp_size_rnd_array[i]],
                        industry=label,
                    )
                    companies.append(company)
        return Companies(companies)

    def __len__(self):
        return len(self.members)

    def __iter__(self):
        return iter(self.members)


def _compute_size_mean(sizegroup: str) -> int:
    """
    Given company size group calculates mean
    """
    # ensure that read_companysize_census() also returns number of companies
    # in each size category
    size_min, size_max = sizegroup.split("-")
    if size_max == "XXX" or size_max == "xxx":
        size_mean = 1500
    else:
        size_min = float(size_min)
        size_max = float(size_max)
        size_mean = (size_max - size_min) / 2.0

    return int(size_mean)


if __name__ == '__main__':
    geography = Geography.from_file(filter_key={"msoa" : ["E02002559"]})
    companies = Companies.for_geography(geography)
    company = companies.members[0]
    print(len(companies))
    print(company.id, company.industry, company.workers)
