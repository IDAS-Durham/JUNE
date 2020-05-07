import numpy as np
from random import uniform
from scipy import stats
import warnings

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""


class CompanyDistributor:
    """
    Distributes workers that are not yet working in key company sectors
    (e.g. such as schools and hospitals) to companies.
    """

    def __init__(self, companies, super_area, config):
        """Get all companies within MSOArea"""
        self.msoarea = super_area
        self.companies = companies
        self.config = config

    def distribute_adults_to_companies(self):
        """
        """
        STUDENT_THRESHOLD = self.config["people"]["student_age_group"]
        ADULT_THRESHOLD = self.config["people"]["adult_threshold"]
        OLD_THRESHOLD = self.config["people"]["old_threshold"]

        for person in self.msoarea.work_people:

            comp_choice = np.random.choice(
                len(self.msoarea.companies), len(self.msoarea.companies), replace=False
            )

            for idx in comp_choice:
                company = self.msoarea.companies[idx]

                if (
                    person.industry == company.industry
                    and company.n_employees < company.n_employees_max
                ):
                    company.n_employees += 1
                    company.n_woman     += person.sex  # remember: woman=1;man=0
                    company.add(person,"worker")
                    break
                # TODO: Take care if cases where people did not find any
                # company at all

        # remove companies with no employees
        for company in self.msoarea.companies:
            if company.n_employees == 0:
                self.msoarea.companies.remove(company)
                self.companies.members.remove(company)
