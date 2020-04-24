import warnings
import numpy as np
from scipy.stats import rv_discrete
from tqdm.auto import tqdm
from covid.groups import Group

class CompanyError(BaseException):
    """Class for throwing company related errors."""
    pass

class Company(Group):
    """
    The Company class represents a company that contains information about 
    its workers (19 - 74 years old).
    """

    def __init__(self, company_id, msoa, n_employees_max, industry):
        super().__init__("Company_%05d" % company_id, "company")
        self.id = company_id
        self.people = []
        self.msoa = msoa
        # set the max number of employees to be the mean number in a range
        self.n_employees_max = n_employees_max
        self.n_employees = 0
        self.n_woman = 0
        self.industry = industry


class Companies:
    def __init__(self, world):
        self.world = world
        self.msoareas = world.msoareas
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
        # companysize_df contains msoarea, and the number of companies of
        # different sizes in that area company_sector_dict contains the
        # number of companies by sector in each msoarea
        # for each msoarea
            # compute a probability distribution over company sizes
            # for each industry
                # for each company in industry
                    # assign company a size_mean according to the probability distribution

        companies = []
        comp_sec_col = self.world.inputs.companysector_df.columns.values.tolist()
        comp_sec_col.remove('msoareas')

        comp_size_col = companysize_df.columns.values
        comp_size_col_encoded = np.arange(1, len(comp_size_col) + 1)
        
        size_dict = {}
        for idx, column in enumerate(comp_size_col):
            size_dict[idx+1] = self._compute_size_mean(column)
        
        #pbar = tqdm(total=len(companysector_df['msoareas']))
        for idx, msoarea_id in enumerate(companysector_df['msoareas']):
            try:

                # create comany size distribution for MSOArea
                companysize_df.loc[msoarea_id]
                distribution = []
                for column in comp_size_col:
                    distribution.append(
                        float(companysize_df.loc[msoarea_id][column]) /\
                        (self._sum_str_elements(companysize_df.loc[msoarea_id],comp_size_col))
                    )
                comp_size_rv = rv_discrete(values=(comp_size_col_encoded,distribution))
                
                # create companies for each sector in MSOArea
                for column in comp_sec_col:

                    comp_size_rnd_array = comp_size_rv.rvs(size=int(companysector_df[column][idx]))
                    for i in range(int(companysector_df[column][idx])):
                        company = Company(
                            company_id=i,
                            msoa=msoarea_id,
                            n_employees_max=size_dict[comp_size_rnd_array[i]],
                            industry=column
                        )
                            
                        companies.append(company)

                        msoaidx = np.where(self.msoareas.ids_in_order == msoarea_id)[0]
                        if len(msoaidx) != 0:
                            self.msoareas.members[msoaidx[0]].companies.append(company)
                        else:
                            #TODO give some warning for verbose
                            pass
 
            except:
                #TODO include verbose option
                warnings.warn(f"The initialization of companies for the MSOArea {0} failed.".format(msoarea))
                pass
            #pbar.update(1)
        #pbar.close()
        self.members = companies
