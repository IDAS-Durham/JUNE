import numpy as np
from scipy.stats import rv_discrete
from tqdm.auto import tqdm

class CompanyError(BaseException):
    """Class for throwing company related errors."""
    pass

class Company:
    """
    The Company class represents a company that contains information about 
    its workers (19 - 74 years old).
    """

    def __init__(self, company_id, msoa, n_employees_max, industry):
        self.id = company_id
        self.people = []
        self.msoa = msoa
        # set the max number of employees to be the mean number in a range
        self.n_employees_max = n_employees_max
        self.n_employees = 0
        self.industry = industry


class Companies:
    def __init__(self, world):
        self.world = world
        #TODO Chr self.members = {}
        self.init_companies(
            world.inputs.companysize_df,
            world.inputs.companysector_df,
        )


    def _compute_size_mean(self, sizegroup):
        '''
        Given company size group calculates mean
        '''
        
        # ensure that read_companysize_census() also returns number of companies
        # in each size category
        size_min, size_max = sizegroup.split('-')
        if size_max == "XXX" or size_max == 'xxx':
            size_mean = 1500
        else:
            size_min = float(size_min)
            size_max = float(size_max)
            size_mean = (size_max - size_min)/2.0

        return int(size_mean)

    def _sum_str_elements(self, df_loc, columns):
        total = 0
        for column in columns:
            total += float(df_loc[column])
        return total
    
    def init_companies(self, companysize_df, companysector_df):
        """
        Initializes all companies across all msoareas
        """

        ## PSEUDO CODE TO DEFINE WHAT IS BEING DONE HERE
        # companysize_df contains msoarea, and the number of companies of different sizes in that area
        # company_sector_dict contains the number of companies by sector in each msoarea
        # for each msoarea
            # compute a probability distribution over company sizes
            # for each industry
                # for each company in industry
                    # assign company a size_mean according to the probability distribution

        
        companies = []
        # need to make sure the dict is set up correctly to do this
        sector_columns = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U']
        size_columns = ["0-9","10-19","20-49","50-99","100-249","250-499","500-999","1000-xxx"]
        size_dict = {}
        for idx, column in enumerate(size_columns):
            size_dict[idx+1] = self._compute_size_mean(column)
        

        pbar = tqdm(total=len(companysector_df['msoareas']))
        for idx, msoarea in enumerate(companysector_df['msoareas']):
            try:
                companysize_df.loc[msoarea]
                
                distribution = []
                for column in size_columns:
                    distribution.append(
                        float(companysize_df.loc[msoarea][column])/(self._sum_str_elements(companysize_df.loc[msoarea],size_columns))
                    )
                numbers = np.arange(1,9)
                random_variable = rv_discrete(values=(numbers,distribution))
                for column in sector_columns:
                    for i in range(int(companysector_df[column][idx])):
                        company = Company(
                            company_id=i,
                            msoa=msoarea,
                            n_employees_max=size_dict[random_variable.rvs(size=1)[0]],
                            industry=column
                        )
                            
                companies.append(company)
            except:
                pass
            pbar.update(1)
        pbar.close()

        self.members = companies
