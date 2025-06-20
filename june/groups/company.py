import logging
import random
from enum import IntEnum
from random import shuffle
from june import paths
from typing import List
import yaml

import numpy as np
import pandas as pd

from june.epidemiology.infection.disease_config import DiseaseConfig
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

    __slots__ = ("super_area", "sector", "n_workers_max")

    def __init__(self, super_area=None, n_workers_max=np.inf, sector=None, registered_members_ids=None):
        """
        Initialize a Company instance.

        Parameters
        ----------
        disease_config : DiseaseConfig
            Configuration object for the disease.
        super_area : str, optional
            The area the company belongs to.
        n_workers_max : int, optional
            Maximum number of workers the company can accommodate (default is np.inf).
        sector : str, optional
            The sector the company belongs to.
        registered_members_ids : dict, optional
            A dict mapping subgroup IDs to lists of member IDs.
        """
        # Initialize the base Group class with disease_config
        super().__init__()

        # Assign attributes specific to Company
        self.super_area = super_area
        self.sector = sector
        self.n_workers_max = n_workers_max
        
        # Initialize registered_members_ids as a dictionary
        self.registered_members_ids = registered_members_ids if registered_members_ids is not None else {}

    def add(self, person):
        super().add(
            person,
            subgroup_type=self.get_index_subgroup(person),
            activity="primary_activity",
        )

    def add_to_registered_members(self, person_id, subgroup_type=0):
        """
        Add a person to the registered members list for a specific subgroup.
        
        Parameters
        ----------
        person_id : int
            The ID of the person to add
        subgroup_type : int, optional
            The subgroup to add the person to (default: 0)
        """
        # Create the subgroup if it doesn't exist
        if subgroup_type not in self.registered_members_ids:
            self.registered_members_ids[subgroup_type] = []
            
        # Add the person if not already in the list
        if person_id not in self.registered_members_ids[subgroup_type]:
            self.registered_members_ids[subgroup_type].append(person_id)

    @property
    def n_workers(self):
        return len(self.people)

    # @property
    # def workers(self):
    #     return self.subgroups[self.SubgroupType.workers]

    @property
    def coordinates(self):
        return self.super_area.coordinates

    @property
    def area(self):
        return self.super_area.areas[0]

    def get_interactive_group(self, people_from_abroad=None):
        return InteractiveCompany(self, people_from_abroad=people_from_abroad)


class Companies(Supergroup):
    venue_class = Company

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
        sector_nr_per_msoa_file: str = default_sector_nr_per_msoa_file
    ) -> "Companies":
        """
        Creates companies for the specified geography, and saves them
        to the super_areas they belong to.
        """
        if not geography.super_areas:
            raise CompanyError("Empty geography!")
        # After creating the companies
        companies = cls.for_super_areas(
            geography.super_areas,
            size_nr_file,
            sector_nr_per_msoa_file
        )
        logger.info(f"There are {len(companies)} companies in this geography.")


        # Sample 5 companies from each super area for visualization
        sampled_companies = []
        for super_area in geography.super_areas:
            if hasattr(super_area, 'companies') and super_area.companies:
                # Sample 5 companies or fewer if there are less than 5
                sample_companies = random.sample(super_area.companies, min(5, len(super_area.companies)))
                for company in sample_companies:
                    sampled_companies.append({
                        "| Company ID": company.id,
                        "| Super Area": super_area.name,
                        "| Company Sector": company.sector,
                        "| Number of Workers": company.n_workers,
                        "| Coordinates": company.coordinates,
                        "| Max Workers": company.n_workers_max
                    })

        # Convert the sample data to a DataFrame
        df_companies = pd.DataFrame(sampled_companies)
        print("\n===== Sample of Created Companies =====")
        print(df_companies)

        return companies

    @classmethod
    def for_super_areas(
        cls,
        super_areas: List[SuperArea],
        size_nr_per_super_area_file: str = default_size_nr_file,
        sector_nr_per_super_area_file: str = default_sector_nr_per_msoa_file
        ) -> "Companies":
        """
        Creates companies for the specified super_areas, and saves them
        to the super_areas they belong to.
        """
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
                super_area, company_sizes_per_super_area, company_sectors_per_super_area
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
                    super_area, company_sizes, company_sectors
                )
                companies += super_area.companies

        
        return cls(companies)

    @classmethod
    def create_companies_in_super_area(
        cls, super_area: SuperArea, company_sizes, company_sectors
    ) -> list:
        """
        Creates companies in a super area using the sizes and sectors distributions.
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
        """
        Create a company instance.

        Parameters
        ----------
        super_area : SuperArea
            The area the company belongs to.
        company_size : int
            Maximum number of workers the company can accommodate.
        company_sector : str
            The sector the company belongs to.
        disease_config : DiseaseConfig
            Configuration object for the disease.

        Returns
        -------
        Company
            A new company instance.
        """
        company = cls.venue_class(
            super_area=super_area,
            n_workers_max=company_size,
            sector=company_sector,
            registered_members_ids={}  # Initialize as an empty dictionary for subgroup support
        )
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
            betas=betas, beta_reductions=beta_reductions
        )
        return beta_processed * self.sector_betas.get(self.sector, 1.0)
