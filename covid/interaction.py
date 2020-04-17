from covid.infection import Infection
from covid.groups import Group
import numpy as np
import sys
import random

class Interaction:
    allowed_severe_tags = ["none", "constant", "differential"]
    
    def __init__(self, infection_selector, config):
        self.selector = infection_selector
        self.params   = config["interaction"]
        self.groups   = []
        self.time     = 0.0
        self.oldtime  = 0.0
        self.delta_t  = 0.0
        self.init()
        self.init_severe_treatment()

    def init(self):
        pass
                
    def init_severe_treatment(self):
        if "severe_treatment" in self.params["parameters"]:
            if "type" in self.params["parameters"]["severe_treatment"]:
                self.severe = self.params["parameters"]["severe_treatment"]["type"]
                if not (self.severe in self.allowed_severe_tags):
                    self.severe = "constant"
                ### in the IC model this is a constant
            if "omega" in self.params["parameters"]["severe_treatment"]:
                self.omega  = self.params["parameters"]["severe_treatment"]["omega"]
        self.psi      = {}
        for grouptype in Group.allowed_groups:
            value = 1.
            if "severe_treatment" in self.params["parameters"]:
                if grouptype in self.params["parameters"]["severe_treatment"]:
                    label = grouptype+"_severity_factor"
                    value = self.params["parameters"]["severe_treatment"][label]
            self.psi[grouptype] = value
                
            
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

    def severity_multiplier(self, grouptype):
        factor = 1.
        if self.severe=="constant":
            tag = person.get_symptons_tag()
            if (tag=="influenza-like illness" or tag=="pneumonia" or
                tag=="hospitalised" or tag=="intensive care"):
                factor *= (self.omega * self.psi[grouptype] - 1.)
        elif self.severe=="differential":
                factor *= (1.+self.omega*self.psi[grouptype]*person.get_severity(self.time))
        return factor

    def single_time_step_for_group(self, group):
        pass












