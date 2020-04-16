import numpy as np

def assign_adults_to_company(person,live_oarea, work_msoarea, industry):

    # for person who works in msoarea - already done in the function inside which this will be called
        # get industry of person
        # randomly sample from all compaies who are in a given industry until find one that isn't full?
        # could also do this the other way around???
        # company = randomly choose company based on size distribution(?)
        # assign person to company


class CompanyDistributor:
    """
    Distributes students to different schools
    """

    def __init__(self, msoarea):
        self.area = msoareadef __init__(self, msoarea, companies):
        self.area = msoarea
        self.companies_all = companies
        # gather call companies in a given msoarea
        self.companies_msoarea = []
        for company in self.companies.members:
            if company.msoa == msoarea:
                self.companies_msoarea.append(company)

    def _randomly_sample_company(self):
        index = np.random.randint(len(self.companies_msoarea))
        return self.companies_msoarea[index]

    def distribute_adults_to_companies(self):
        # this assumes that self.msoarea.people.values() gives the people who WORK in that area
        for person in self.msoarea.people.values():
            if (
                    person.age <= self.WORK_AGE_RANGE[1] # if we already assume the first comment, this seems redundant
                and person.age >= self.WORK_AGE_RANGE[0]
            ):  # person age from 20 up to 74 yo
                person_industry = person.industry
                assigned = False
                while assigned == False:
                    # randomly sample from companies in msoarea rather than filling from the start
                    # as not all companies will be filled and there may be a mismatch in the number of people
                    # and the number of companies
                    company = self._randomly_sample_company()
                    if company.n_employees == company.n_employees_max:
                            pass
                    else:
                        company.n_employees +=1
                        assigned = True
    
