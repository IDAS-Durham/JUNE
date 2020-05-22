from collections import defaultdict

import numpy as np

from june.groups import Companies

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

    def distribute_adults_to_companies_in_super_areas(self, super_areas):
        for super_area in super_areas:
            self.distribute_adults_to_companies_in_super_area(super_area)

    def distribute_adults_to_companies_in_super_area(self, super_area):
        """
        Looks for all workers and companies in the super area and matches
        them
        """
        company_dict = defaultdict(list)
        full_idx = defaultdict(int)
        unallocated_workers = []
        for company in super_area.companies:
            company_dict[company.sector].append(company)
            full_idx[company.sector] = 0

        for worker in super_area.workers:
            if worker.primary_activity is not None:
                continue
            if company_dict[worker.sector]:
                if full_idx[worker.sector] >= len(company_dict[worker.sector]):
                    company = np.random.choice(company_dict[worker.sector])
                else:
                    company = company_dict[worker.sector][0]
                    if company.n_workers >= company.n_workers_max:
                        full_idx[company.sector] += 1
                company.add(worker)
            else:
                unallocated_workers.append(worker)

        if unallocated_workers:
            companies_for_unallocated = np.random.choice(
                super_area.companies, len(unallocated_workers)
            )
            for worker, company in zip(unallocated_workers, companies_for_unallocated):
                company.add(worker)

