from collections import defaultdict
import logging
import numpy as np
from random import randint


from june.groups import Companies

logger = logging.getLogger("company_distributor")

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
        logger.info(f"Distributing workers to companies")
        for i, super_area in enumerate(super_areas):
            if i % 100 == 0:
                logger.info(f"Distributed workers to companies in {i} of {len(super_areas)} super areas.")
            self.distribute_adults_to_companies_in_super_area(super_area)
        logger.info(f"Workers distributed to companies")

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
                    idx = randint(0, len(company_dict[worker.sector]) - 1)
                    company = company_dict[worker.sector][idx]
                    #company = np.random.choice(company_dict[worker.sector])
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
