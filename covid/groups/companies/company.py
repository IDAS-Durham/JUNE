class CompanyError(BaseException):
    """Class for throwing company related errors."""
    pass

class Company:
    """
    The Company class represents a company that contains information about 
    its workers (19 - 74 years old).
    """

    def __init__(self, company_id, msoa, n_employees):
        self.id = company_id
        self.people = []
        self.msoa = msoa
        self.n_employees_max = n_employees
        self.n_employees
        self.size_mean
        self.industry

class Companies:
    def __init__(self, world, msoareas, companysize_dict):
        self.world = world
        self.members = {}
        self.init_companies(companysize_dict)


    def _compute_size_mean(self, sizegroup):
        '''
        Given company size group calculates mean
        '''
        
        # ensure that read_companysize_census() also returns number of companies in each size category
        size_min, size_max = sizegroup.split('-')
        if age_2 == "XXX":
            agemean = 1500
        else:
            size_min = float(size_min)
            size_max = float(size_max)
            size_mean = (size_max - size_min)/2.0

        return size_mean
    
    def init_companies(self, companysize_dict, companysector_dict):
        """
        Initializes Companies.
        """
        # companysize_dict contains msoarea, and the number of companies of different sizes in that area
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
        
        for msoarea in range(len(companysector_dict['msoarea'])):
            company_total = int(companysector_dict['n_companies'][msoarea])
            distribution = []
            for column in size_columns:
                distribution.append(int(companysize_dict[column][msoarea])/total)

            numbers = np.arange(1,9)
            # gives a discrete distribution over the company size per msoarea
            random_variable = rv_discrete(values=(numbers,distribution))
            for column in sector_columns:
                for company in range(column[msoarea]):
                    # finish this
                                          
                    
                
        

        
            {}
        )  # stores for each gender-ratio group the index to the school
        # create company neighbour trees
        for agegroup in school_age:
            school_agegroup_to_global_indices[
                agegroup
            ] = {}  # this will be used to track school universally
            mean = self._compute_age_group_mean(agegroup)
            _school_df_agegroup = school_df[
                (school_df["age_min"] <= mean) & (school_df["age_max"] >= mean)
            ]
            school_trees[agegroup] = self._create_school_tree(_school_df_agegroup)
        # create schools and put them in the right age group
        for i, (index, row) in enumerate(school_df.iterrows()):
            school = School(
                i,
                np.array(row[["latitude", "longitude"]].values, dtype=np.float64),
                row["NOR"],
                row["age_min"],
                row["age_max"],
            )
            # to which age group does this school belong to?
            for agegroup in school_age:
                agemean = self._compute_age_group_mean(agegroup)
                if school.age_min <= agemean and school.age_max >= agemean:
                    school_agegroup_to_global_indices[agegroup][
                        len(school_agegroup_to_global_indices[agegroup])
                    ] = i
            schools.append(school)
        # store variables to class
        self.members = schools
        self.school_trees = school_trees
        self.school_agegroup_to_global_indices = school_agegroup_to_global_indices
        return None
        

