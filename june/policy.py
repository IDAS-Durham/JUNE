


class Policy:
    '''
    Implement certain policy decisions into the simulartor
    Policies should be implemented in a modular fashion applying one after the other

    Assumptions:
    - If alpha and beta values are changed this is done by social distancing
      This means that this function must be called first
    - Any functions making edits to the active subgroups of a person assume that there is an attribute person.policy_subgroups
      This attribute is all the groups which will be accessed under and policy implementations
      To undo a policy this attribute has to be reset and the fraction implemented again
      This can be done by running the open_all() function

      e.g. full school closure:
           school_closure(person, years = None, full_closure = True)
           now reopen only certain schools:
           open_all()
           school_closure(person, years = [...], full_closure = False)

    - Many things rely on the the knowledge of key workers - let this be decided by whether or not their companies are closed
    '''

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
        
        -----------
        Parameters:
        person: a member of the Persons class
        '''

        person.policy_subgroup = person.subgroups
        

    def quarantine(self):

        # if symptoms: quarantine for x days
        # if live with symptoms: quarantine for y days
        # if released from quarantine: quarantine for z days
        
        pass

    #def categorise_key_workers(self, person):
    #
    #    if person.age not in ['WORK AGE BRACKET']:
    #        raise ValueError('Person passed must be of working age')
    #
    #    if self.config_file is not None:
    #        if person.company is not None:
                
            

    def school_closure(self, person, years, full_closure = False):
        '''
        Implement school closure by year group
        
        ----------
        Parametes:
        person: member of the Persons class and is a child
        years: (list) year groups to close schools with
        full_closure: (bool) if True then all years closed, otherwise only close certain years
        '''

        if person.age not in ['SCHOOL AGE BRACKET']:
            raise ValueError('Person passed must be of school age')
        
        # This will currently not work and is more like pseudocode
        if full_closure:
            person.policy_subgroup.pop('school')
        else:
            if person.age is in years:

                # check if BOTH parents are in work or not
                working = True:
                for parent in person.parents:
                    if 'company' not in parent.policy_subgroups:
                        working = False
                        break

                # if BOTH parents are not working then do not send child to school
                if not working:
                    person.policy_subgroups.pop('school')
                                   
    
    def company_closure(self, person, sectors, full_closure = False):
        '''
        Close companies by sector
        
        -----------
        Parameters:
        person: member of the Persons class
        sectors: (list) sectors to be closed
        full_closure: (bool) if True then all sectorsclosed, otherwise only close certain sectors
        '''
        
        if person.age not in ['WORK AGE BRACKET']:
            raise ValueError('Person passed must be of working age')

        if full_closue
        
    def leisure_closure(self, venues, full_closure):

        # uses adherence?
        # closes leisure by venue type e.g. pub, cinema etc.
    
    def social_distancing(self, alpha, betas):
        '''
        Implement social distancing policy
        
        -----------
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
        
        if self.config_file is not None:
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
