from covid.infection import Infection
from covid.groups import Group
import numpy as np
import sys
import random


class Interaction:
    def __init__(self, infection_selector, config):
        self.selector = infection_selector
        self.params   = config["interaction"]
        self.groups   = []
        self.time     = 0.0
        self.oldtime  = 0.0
        self.delta_t  = 0.0
        self.transmission_probability = 0.0
        self.init()

    def init(self):
        pass
        
    def set_groups(self, groups):
        self.groups = groups

    def set_time(self, time):
        self.oldtime = self.time
        self.time = time
        self.delta_t = self.time - self.oldtime

    def time_step(self):
        #print("================ BEFORE ====================")
        #n_inf0 = 0
        #n_rec0 = 0
        #n_sus0 = 0
        for grouptype in self.groups:
            for group in grouptype.members:
                if group.size() != 0:
                    group.update_status_lists(self.time)
                #n_inf0 += group.size_infected() 
                #n_rec0 += group.size_recovered() 
                #n_sus0 += group.size_susceptible()
        #print ("Total at time = ",self.oldtime,", ",(n_inf0+n_rec0+n_sus0)," people:")
        #print ("   ",n_inf0,"infected, ",n_rec0," recovered,",n_sus0," healthy people")
        #print ("Start the time step with duration = ",(self.delta_t*24.)," hours") 
        for grouptype in self.groups:
            for group in grouptype.members:
                if group.size() != 0:
                    self.single_time_step_for_group(group)
        #print("================ AFTER =====================")
        #n_inf1 = 0
        #n_rec1 = 0
        #n_sus1 = 0
        for grouptype in self.groups:
            for group in grouptype.members:
                if group.size() != 0:
                    group.update_status_lists(self.time)
                #n_inf1 += group.size_infected() 
                #n_rec1 += group.size_recovered() 
                #n_sus1 += group.size_susceptible() 
        #print ("Ended the time step at time = ",self.time,".")
        #print ("Total at time = ",self.oldtime,", ",(n_inf1+n_rec1+n_sus1)," people:")
        #print ("   ",n_inf1,"infected, ",n_rec1," recovered,",n_sus1," healthy people")
        #print ("============================================")
        #print ("============================================")
        #print ("============================================")

    def single_time_step_for_group(self, group):
        pass


