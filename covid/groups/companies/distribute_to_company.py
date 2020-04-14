import numpy as np

def assign_adults_to_company(person,live_oarea, work_msoarea, industry):

    # for person who works in msoarea - already done in the function inside which this will be called
        # get industry of person
        # randomly sample from all compaies who are in a given industry until find one that isn't full?
        # could also do this the other way around???
        # company = randomly choose company based on size distribution(?)
        # assign person to company

    # gather companies to be sampled from - this should be included in the __init__ function as per the SchoolDistirbutor
    def __init__(self, msoarea, companies):
        self.area = msoarea
        self.companies_all = companies
        # gather call companies in a given msoarea
        self.companies_msoarea = []
        for company in self.companies.members:
            if company.msoa == msoarea:
                self.companies_msoarea.append(company)
        

    ########## PROCEED WITH FUNCTION ##############

    person_industry = person.industry
    for company in self.companies_msoarea:
        if company.industry == person_industry:
            if company.n_employees == company.n_employees_max:
                pass
            else:
                company.n_employees +=1
                break
    
    
