from collections import defaultdict
import logging
import numpy as np
import pandas as pd
import random
from random import randint


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
        logger.info("Distributing workers to companies")
        distributed_workers_data = []  # Collect data for visualization
        for i, super_area in enumerate(super_areas):
            if i % 100 == 0:
                logger.info(
                    f"Distributed workers to companies in {i} of {len(super_areas)} super areas."
                )
            self.distribute_adults_to_companies_in_super_area(super_area)

            # After distribution, iterate over companies to find which company each worker belongs to
            for company in super_area.companies:
                for worker in company.people:  # Assuming `people` holds the list of assigned workers
                    distributed_workers_data.append({
                        "| Person ID": worker.id,
                        "| Home Area": worker.area.name,
                        "| Person Age": worker.age,
                        "| Assigned Work Super Area": worker.work_super_area.name if worker.work_super_area else "No Assignment",
                        "| Assigned Work Sector": getattr(worker, 'sector', None),
                        "| Lockdown Status": getattr(worker, 'lockdown_status', None),
                        "| Assigned Company ID": company.id,
                        "| Company Sector": company.sector
                    })

        # Sample final distribution across all super areas
        all_companies = [
            {
                "| Super Area": super_area.name,
                "| Company ID": company.id,
                "| Sector": company.sector,
                "| Worker IDs": [worker.id for worker in random.sample(company.people, min(5, len(company.people)))],
                "| Number of Workers": len(company.people),
                "| Max Capacity": company.n_workers_max
            }
            for super_area in super_areas
            for company in super_area.companies
        ]
        
        # Convert data to DataFrame for visualization
        df_companies = pd.DataFrame(all_companies)
        print("\n===== Sample of Companies after Distributing Workers =====")
        print(df_companies.sample(10))  # Adjust sample size as needed
        
        # Show a preview of registered_members_ids for some companies
        registered_members_preview = []
        
        # Safely sample up to 5 super areas
        sample_super_areas = random.sample(list(super_areas), min(5, len(super_areas))) if super_areas else []
        
        for super_area in sample_super_areas:
            # Skip if no companies
            if not hasattr(super_area, 'companies') or not super_area.companies:
                continue
                
            # Sample companies safely
            sample_companies = random.sample(list(super_area.companies), min(3, len(super_area.companies)))
            
            for company in sample_companies:
                if not hasattr(company, 'registered_members_ids'):
                    continue
                    
                # Format dictionary data for display
                total_members = sum(len(members) for members in company.registered_members_ids.values())
                all_sample_ids = []
                for subgroup_id, members in company.registered_members_ids.items():
                    if members:
                        # Take up to 2 members from each subgroup to show in sample
                        all_sample_ids.extend([(subgroup_id, member_id) for member_id in members[:2]])
                
                # Format sample IDs for display with subgroup indicators
                sample_display = [f"sg{sg}:{id}" for sg, id in all_sample_ids[:5]]
                
                registered_members_preview.append({
                    "| Company ID": company.id,
                    "| Super Area": super_area.name,
                    "| Sector": company.sector,
                    "| Registered Members Count": total_members,
                    "| Subgroups": list(company.registered_members_ids.keys()),
                    "| Sample Registered Member IDs": sample_display
                })
        
        if registered_members_preview:  # Only create DataFrame if we have data
            df_registered = pd.DataFrame(registered_members_preview)
            print("\n===== Sample of Companies' Registered Member IDs =====")
            print(df_registered)

        # Convert to DataFrame for visualization
        df_distributed_workers = pd.DataFrame(distributed_workers_data).sample(10)  # Show random sample of 10
        print("\n===== Sample of Distributed Workers with Company Assignments =====")
        print(df_distributed_workers)
        logger.info(f"{len(distributed_workers_data)} Workers distributed with company assignments.")

        logger.info("Workers distributed to companies")

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
                else:
                    company = company_dict[worker.sector][0]
                    if company.n_workers >= company.n_workers_max:
                        full_idx[company.sector] += 1
                company.add(worker)
                # Use the numeric subgroup index directly
                subgroup = company.get_index_subgroup(worker)
                company.add_to_registered_members(worker.id, subgroup_type=subgroup)

            else:
                unallocated_workers.append(worker)

        if unallocated_workers:
            companies_for_unallocated = np.random.choice(
                super_area.companies, len(unallocated_workers)
            )
            for worker, company in zip(unallocated_workers, companies_for_unallocated):
                company.add(worker)
                # Use the numeric subgroup index directly
                subgroup = company.get_index_subgroup(worker)
                company.add_to_registered_members(worker.id, subgroup_type=subgroup)
