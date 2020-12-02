import logging
from enum import IntEnum
from random import shuffle
from june import paths
from typing import List
import h5py
import yaml

import numpy as np
import pandas as pd

from june.geography import Geography, SuperArea
from june.groups import Group, Supergroup
from june.groups.group.interactive import InteractiveGroup

default_size_nr_file = paths.data_path / "input/companies/company_size_2011.csv"
default_sector_nr_per_msoa_file = (
    paths.data_path / "input/companies/company_sector_2011.csv"
)
default_areas_map_path = paths.data_path / "input/geography/area_super_area_region.csv"
default_config_filename = paths.configs_path / "defaults/groups/companies.yaml"

logger = logging.getLogger(__name__)


def _get_size_brackets(sizegroup: str):
    """
    Given company size group calculates mean
    """
    # ensure that read_companysize_census() also returns number of companies
    # in each size category
    size_min, size_max = sizegroup.split("-")
    if size_max == "XXX" or size_max == "xxx":
        size_min = int(size_min)
        size_max = 1500
    else:
        size_min = int(size_min)
        size_max = int(size_max)
    return size_min, size_max


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

    __slots__ = (
        "super_area",
        "sector",
        "n_workers_max",
    )

    class SubgroupType(IntEnum):
        workers = 0

    def __init__(self, super_area=None, n_workers_max=np.inf, sector=None):
        super().__init__()
        self.super_area = super_area
        self.sector = sector
        self.n_workers_max = n_workers_max

    def add(self, person):
        super().add(
            person,
            subgroup_type=self.SubgroupType.workers,
            activity="primary_activity",
        )

    @property
    def n_workers(self):
        return len(self.people)

    @property
    def workers(self):
        return self.subgroups[self.SubgroupType.workers]

    @property
    def coordinates(self):
        return self.super_area.coordinates

    @property
    def area(self):
        return self.super_area.areas[0]

    def get_interactive_group(self, people_from_abroad=None):
        return InteractiveCompany(self, people_from_abroad=people_from_abroad)


class Companies(Supergroup):
    def __init__(self, companies: List["Companies"]):
        """
        Create companies and provide functionality to allocate workers.

        Parameters
        ----------
        company_size_per_superarea_df: pd.DataFram
            Nr. of companies within a size-range per SuperArea.

        compsec_per_msoa_df: pd.DataFrame
            Nr. of companies per sector sector per SuperArea.
        """
        super().__init__(members=companies)

    @classmethod
    def for_geography(
        cls,
        geography: Geography,
        size_nr_file: str = default_size_nr_file,
        sector_nr_per_msoa_file: str = default_sector_nr_per_msoa_file,
        default_config_filename: str = default_config_filename,
    ) -> "Companies":
        """
        Creates companies for the specified geography, and saves them 
        to the super_aresa they belong to
        Parameters
        ----------
        geography
            an instance of the geography class
        company_size_per_superarea_filename: 
            Nr. of companies within a size-range per SuperArea.
        compsec_per_msoa_filename: 
            Nr. of companies per sector sector per SuperArea.
        """
        if not geography.super_areas:
            raise CompanyError("Empty geography!")
        return cls.for_super_areas(
            geography.super_areas,
            size_nr_file,
            sector_nr_per_msoa_file,
            default_config_filename,
        )

    @classmethod
    def for_super_areas(
        cls,
        super_areas: List[SuperArea],
        size_nr_per_super_area_file: str = default_size_nr_file,
        sector_nr_per_super_area_file: str = default_sector_nr_per_msoa_file,
        default_config_filename: str = default_config_filename,
    ) -> "Companies":
        """Creates companies for the specified super_areas, and saves them 
        to the super_aresa they belong to
        Parameters
        ----------
        super_areas
            list of super areas
        company_size_per_superarea_filename: 
            Nr. of companies within a size-range per SuperArea.
        compsec_per_msoa_filename: 
            Nr. of companies per industry sector per SuperArea.

        Parameters
        ----------
        """
        with open(default_config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        size_per_superarea_df = pd.read_csv(size_nr_per_super_area_file, index_col=0)
        sector_per_superarea_df = pd.read_csv(
            sector_nr_per_super_area_file, index_col=0
        )
        super_area_names = [super_area.name for super_area in super_areas]
        company_sizes_per_super_area = size_per_superarea_df.loc[super_area_names]
        company_sectors_per_super_area = sector_per_superarea_df.loc[super_area_names]
        assert len(company_sectors_per_super_area) == len(company_sizes_per_super_area)
        if len(company_sectors_per_super_area) == 1:
            super_area = super_areas[0]
            companies = cls.create_companies_in_super_area(
                super_area,
                company_sizes_per_super_area,
                company_sectors_per_super_area,
            )
            super_area.companies = companies
        else:
            companies = []
            for super_area, (_, company_sizes), (_, company_sectors) in zip(
                super_areas,
                company_sizes_per_super_area.iterrows(),
                company_sectors_per_super_area.iterrows(),
            ):
                super_area.companies = cls.create_companies_in_super_area(
                    super_area, company_sizes, company_sectors,
                )
                companies += super_area.companies
        return cls(companies)

    @classmethod
    def create_companies_in_super_area(
        cls, super_area: SuperArea, company_sizes, company_sectors,
    ) -> list:
        """
        Crates companies in super area using the sizes and sectors distributions.
        """
        sizes = np.array([])
        for size_bracket, counts in company_sizes.items():
            size_min, size_max = _get_size_brackets(size_bracket)
            sizes = np.concatenate(
                (sizes, np.random.randint(max(size_min, 1), size_max, int(counts)))
            )
        np.random.shuffle(sizes)
        sectors = []
        for sector, counts in company_sectors.items():
            sectors += [sector] * int(counts)
        shuffle(sectors)
        companies = list(
            map(
                lambda company_size, company_sector: cls.create_company(
                    super_area, company_size, company_sector
                ),
                sizes,
                sectors,
            )
        )
        return companies

    @classmethod
    def create_company(cls, super_area, company_size, company_sector):
        company = Company(super_area, company_size, company_sector)
        return company


def _read_sector_betas():
    with open(default_config_filename) as f:
        sector_betas = yaml.load(f, Loader=yaml.FullLoader) or {}
    return sector_betas


class InteractiveCompany(InteractiveGroup):
    sector_betas = _read_sector_betas()

    def __init__(self, group: "Group", people_from_abroad=None):
        super().__init__(group=group, people_from_abroad=people_from_abroad)
        self.sector = group.sector

    def get_processed_beta(self, betas, beta_reductions):
        beta_processed = super().get_processed_beta(
            betas=betas,
            beta_reductions=beta_reductions,
        )
        return beta_processed * self.sector_betas.get(self.sector, 1.0)
