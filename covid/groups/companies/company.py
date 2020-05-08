import logging
from enum import IntEnum
from itertools import count

import numpy as np
import pandas as pd
from scipy.stats import rv_discrete
from typing import List, Tuple

from covid.groups import Group

ic_logger = logging.getLogger(__name__)


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

    class GroupType(IntEnum):
        worker = 0

    def __init__(self, msoa=None, n_employees_max=np.inf, industry=None):
        super().__init__(name="Company_{company_id}", spec="company")
        self.msoa = msoa
        # set the max number of employees to be the mean number in a range
        self.n_employees_max = n_employees_max
        self.n_woman = 0
        self.employees = []
        self.industry = industry

    def add(self, person, qualifier=GroupType.worker):
        super().add(person, qualifier)
        person.company = self


class Companies:
    def __init__(self, companies: List["Companies"]):
        """
        Create companies and provide functionality to allocate workers.

        Parameters
        ----------
        company_size_per_superarea_df: pd.DataFram
            Nr. of companies within a size-range per MSOA.

        compsec_per_msoa_df: pd.DataFrame
            Nr. of companies per industry sector per MSOA.
        """
        self.members = companies

    @classmethod
    def from_df(
        cls, company_size_per_superarea_df: str, company_sector_per_superarea_df: str
    ) -> "Companies":
        """
        Initializes Companies class from a list of companies read from a DataFrame.

        Parameters
        ----------
        companysize_file
            Pandas dataframe with number of companies within a size-range per MSOA.
        company_per_sector_per_msoa_file
            Pandas dataframe with number of companies per industry sector per MSOA.
        """
        companies = []

        compsize_labels = company_size_per_superarea_df.columns.values
        compsize_labels_encoded = np.arange(1, len(compsize_labels) + 1)
        companysize_data_per_area = company_size_per_superarea_df.values
        company_per_sector_data_per_area = company_sector_per_superarea_df.values

        size_dict = {
            (idx + 1): _compute_size_mean(size_label)
            for idx, size_label in enumerate(compsize_labels)
        }
        msoa_names = company_size_per_superarea_df.index.values
        # Run through each MSOArea
        compsec_labels = company_sector_per_superarea_df.columns
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
                # Run through all companies within sector within MSOA
                for i in range(int(nr_of_comp)):
                    company = Company(
                        msoa=msoa_names[area_counter],
                        n_employees_max=size_dict[comp_size_rnd_array[i]],
                        industry=label,
                    )

                    companies.append(company)
        return cls(companies)

    @classmethod
    def from_file(
        cls, companysize_file: str, company_per_sector_file: str,
    ) -> "Companies":
        """
        Parameters
        ----------
        companysize_file: str
        company_per_sector_per_msoa_file: str
        """
        company_size_per_superarea_df = pd.read_csv(companysize_file, index_col=0)
        company_size_per_superarea_df = company_size_per_superarea_df.div(
            company_size_per_superarea_df.sum(axis=1), axis=0
        )
        company_sector_per_superarea_df = pd.read_csv(
            company_per_sector_file, index_col=0
        )
        return Companies.from_df(
            company_size_per_superarea_df, company_sector_per_superarea_df
        )
