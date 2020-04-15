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


class CollectiveInteraction(Interaction):
    def single_time_step_for_group(self, group):
        if (
            group.size() <= 1
            or group.size_infected() == 0
            or group.size_susceptible() == 0
        ):
            return
        transmission_probability = self.calculate_transmission_probability(group)
        if transmission_probability <= 0.0:
            return
        for recipient in group.get_susceptible():
            self.single_time_step_for_recipient(recipient, transmission_probability)

    def single_time_step_for_recipient(self, recipient, transmission_probability):
        recipient_probability = recipient.get_susceptibility()
        if recipient_probability > 0.0:
            if random.random() <= transmission_probability * recipient_probability:
                recipient.set_infection(
                    self.selector.make_infection(recipient, self.time)
                )

    def calculate_transmission_probability(self, group):
        transmission_probability = 0.0
        if self.mode == "Superposition":
            transmission_probability = self.added_transmission_probability(group)
        elif self.mode == "Probabilistic":
            transmission_probability = self.combined_transmission_probability(group)
        return transmission_probability

    def combined_transmission_probability(self, group):
        """
        multiplicative probability from product of non-infection probabilities.
        for each time step, the infection probabilities per infected person are given
        by their indibidual, time-dependent infection probability times the
        interaction intensity normalised to the group size --- this is to recover the
        logic of the SI/SIR models --- and normalised to the time interval, given in
        units of full days.
        """
        interaction_intensity = group.get_intensity() / max(1,group.size()-1) * self.delta_t
        prob_notransmission = 1.0
        for person in group.get_infected():
            prob_notransmission *= (
                1.0 - person.transmission_probability(self.time) * interaction_intensity
            )
        return 1.0 - prob_notransmission

    def added_transmission_probability(self,group):
        """
        added probability from product of non-infection probabilities.
        for each time step, the infection probabilities per infected person are given
        by their indibidual, time-dependent infection probability times the
        interaction intensity normalised to the group size --- this is to recover the
        logic of the SI/SIR models --- and normalised to the time interval, given in
        units of full days.
        """
        interaction_intensity = group.get_intensity() / max(group.size()-1,1) * self.delta_t
        prob_transmission = 0.0
        for person in group.get_infected():
            prob_transmission += person.transmission_probability(self.time)
        return prob_transmission * interaction_intensity

    def pair_sampling_transmission_probability(self, group, grouptype):
        """
        For this method, given a group of size N, we assume there are a total of M interacions
        at a given time step inside the group. We then use the social interaction matrices
        from the BBC pandemic project to sample M age pairs. For this M age pairs, we compute
        the probability of infecting each other, and update accordingly.
        """
        pass
#        N = 50 #TODO
#        pairs_xi = grouptype.pairs_distribution.rvs(N)











