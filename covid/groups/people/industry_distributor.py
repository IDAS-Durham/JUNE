import numpy as np
from scipy.stats import rv_discrete

def assign_industries(gender, employed, msoarea, industry_by_sex_dict):
    '''
    :param gender: (string) male/female
    :param employed: (bool)
    :param msoarea: (string) MSOArea code
    :param industry_by_sex: (dict) dictionary passed from inputs.py/read_industry_by_sex_census()

    :returns: (string) letter of inductry sector

    Given a person's gender, their employment status, their msoarea,
    use the industry_by_sex_dict to assign each person an industry
    according to the generated probability distribution
    '''
    
    if employed == False:
        industry = 'NA'
    else:
        # access relevant probability distribtion according to the person's sex
        if gender == 'male':
            distribution = industry_by_sex_dict[msoarea]['m']
        else:
            distribution = industry_by_sex_dict[msoarea]['f']
        
        # assign industries to numbers A->U = 1-> 21
        industry_dict = {1:'A',2:'B',3:'C',4:'D',5:'E',6:'F',7:'G',8:'H',9:'I',10:'J',
                        11:'K',12:'L',13:'M',14:'N',15:'O',16:'P',17:'Q',18:'R',19:'S',20:'T',21:'U'}

        numbers = np.arange(1,22)
        # create discrete probability distribution
        random_variable = rv_discrete(values=(numbers,distribution))
        # generate sample from distribution
        industry_id = random_variable.rvs(size=1)
        # accss relevant indudtry label
        industry = industry_dict[industry_id[0]]
        
        return industry
