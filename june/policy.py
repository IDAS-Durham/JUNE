


class Policy:

    # want to make this modular so that you could apply policies in combinations - Keras stype

    # input config file -> alter -> altererd config file -> alter again

    # How to alter things:
    ## can read in the beta and alpha physical
    ## could put an additional override group in heirarchy

    # either from config file or from Keras style
    
    def __init__(self, config_file = None, adherence = 1.):

        self.config_file = config_file
        self.adherence = adherence

    def do_nothing(self):
        pass

    def open_all(self, person):
        '''
        Set people back to moving as before
        This is done by resetting all their subgroups to what they had before
        '''

        person.policy_subgroup = person.subgroups
        

    def quarantine(self):

        # if symptoms: quarantine for x days
        # if live with symptoms: quarantine for y days
        # if released from quarantine: quarantine for z days
        
        pass

    def school_closure(self, person, years, full_closure):

        # uses adherence
        
        # close all schools by years (age brackets)
        # need to decide if this is just people not going to school or schools not pulling people in
        # think about key workers

        # Need to change: weight the intensities,

        # This will currently not work and is more like pseudocode
        if person.age is in years:
            person.policy_subgroup.pop('school')
        
        pass
    
    def company_closure(self, sectors, full_closure):

        # uses adherence
        # close companies by sector

    def leisure_closure(self, venues, full_closure):

        # uses adherence?
        # closes leisure by venue type e.g. pub, cinema etc.
    
    def social_distancing(self, alpha, betas):
        '''
        Implement social distancing policy
        
        ----------------
        Parameters:
        alphas: e.g. (float) from DefaultInteraction, e.g. DefaultInteraction.from_file(selector=selector).alpha
        betas: e.g. (dict) from DefaultInteraction, e.g. DefaultInteraction.from_file(selector=selector).beta

        Assumptions:
        - Currently we assume that social distancing is implemented first and this affects all
          interactions and intensities globally
        - Currently we assume that the changes are not group dependent


        TODO:
        - Implement structure for people to adhere to social distancing
        '''
        
        if not self.config_file:
            alpha /= 2
        else:
            alpha /= self.config_file['social distancing']['alpha factor']

        for group in betas:
            
            if not self.config_file:
                betas[group] /= 2
            else:
                betas[group] /= self.config_file['social distancing']['beta factor']

    def lockdown(self):

        # this could be a combination of all

        pass
