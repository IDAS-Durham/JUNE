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
    Distributes people to different companies
    """
    def __init__(self, companies, msoarea):
        """Get all companies within MSOArea"""
        self.msoarea = msoarea
        self.companies_all = companies


    def distribute_adults_to_companies(self):
        STUDENT_THRESHOLD = self.msoarea.world.config["people"]["student_age_group"]
        ADULT_THRESHOLD = self.msoarea.world.config["people"]["adult_threshold"]
        OLD_THRESHOLD = self.msoarea.world.config["people"]["old_threshold"]
        count = 0
        # this assumes that self.msoarea.people.values() gives the people who WORK in that area
        for person in self.msoarea.work_people:
            
            count += 1
            comp_choice = np.random.choice(
                len(self.msoarea.companies), len(self.msoarea.companies), replace=False
            )
            
            for idx in comp_choice:
                company = self.msoarea.companies[idx]

                if person.industry == company.industry:
                    if company.n_employees == company.n_employees_max:
                        #TODO: Take care if cases where people did not find any
                        # company at all
                        pass
                    else:
                        company.n_employees += 1
                        company.n_woman += person.sex  #remember: woman=1;man=0
                        person.company_id = company.id
                        assigned = True
                        break
                else:
                    pass

