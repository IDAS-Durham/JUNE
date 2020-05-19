


class Policy:

    # want to make this modular so that you could apply policies in combinations - Keras stype

    # input config file -> alter -> altererd config file -> alter again

    # How to alter things:
    ## can read in the beta and alpha physical
    ## could put an additional override group in heirarchy

    
    
    def __init__(self, config_file, adherence):

        self.config_file = config_file
        self.adherence = adherence

    def do_nothing(self):
        pass

    def open_all(self):
        pass

    def quarantine(self):

        # if symptoms: quarantine for x days
        # if live with symptoms: quarantine for y days
        # if released from quarantine: quarantine for z days
        
        pass

    def school_closure(self, years, full_closure):

        # uses adherence
        
        # close all schools by years (age brackets)
        # need to decide if this is just people not going to school or schools not pulling people in
        # think about key workers

        # Need to change: weight the intensities, 
        
        pass
    
    def company_closure(self, sectors, full_closure):

        # uses adherence
        # close companies by sector

    def leisure_closure(self, venues, full_closure):

        # uses adherence?
        # closes leisure by venue type e.g. pub, cinema etc.
    
    def social_distancing(self):

        # this could be a contact matrix reduction in certain circumstances e.g. not schoools
        
        pass

    def lockdown(self):

        # this could be a combination of all

        pass

    def weekly_briefing_confusion(self):
        
        pass
