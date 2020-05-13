from random import uniform

import numpy as np
from scipy import stats

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""


class CompanyDistributor:
    """
    Distributes workers that are not yet working in key company sectors
    (e.g. such as schools and hospitals) to companies. This assumes that
    the WorkerDistributor has already been run to allocate workers in
    a super_area
    """

    def __init__(self):
        """Get all companies within SuperArea"""

    def distribute_adults_to_companies_in_super_area(self, super_area):
        """
        Looks for all workers and companies in the super area and matches
        them
        """
        # shuffle companies
        for person in super_area.workers:
            compatible_companies = []
            for company in super_area.companies:
                if person.sector == company.sector:
                    compatible_companies.append(company)
                    if company.n_workers < company.n_workers_max:
                        company.add(person)
                        break
                    
            # allocate randomly if no place for him/her
            if len(compatible_companies) == 0:
                company = np.random.choice(super_area.companies)
            else:
                company = np.random.choice(compatible_companies)

        # remove companies with no employees
        for company in super_area.companies:
            if company.n_workers == 0:
                super_area.companies.remove(company)
