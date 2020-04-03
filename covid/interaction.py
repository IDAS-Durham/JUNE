import infection as Infection
import group     as Group 
import person    as Person
import sys
import random

class Single_Interaction:
    def __init__(self,group,mode):
        self.mode = mode
        if not isinstance(group,Group.Group):
            print ("Error in Interaction.__init__, no group:",group)
            return
        self.group = group
        
    def single_time_step(self,time,infection_selector):
        if (self.group.size_infected() == 0 or self.group.size_susceptible() == 0): 
            return
        transmission_probability = 0.
        if self.mode=="Superposition":
            transmission_probability = self.added_transmission_probability(time)
        elif self.mode=="Probabilistic":
            transmission_probability = self.combined_transmission_probability(time)
        for recipient in self.group.healthy_people():
            susceptibility        = recipient.get_susceptibility()
            interaction_intensity = self.group.get_intensity()
            recipient_probability = susceptibility * interaction_intensity
            if random.random() < transmission_probability * recipient_probability
                person.set_infection(infection_selector.make_infection(time))
                
    def combined_transmission_probability(self,recipient,time):
        prob_notransmission   = 1.
        for person in self.group.infected_people():
            prob_notransmission *= (1.-person.transmission_probability(time))
        return 1.-prob_notransmission

    def added_transmission_probability(self,recipient,time):
        prob_transmission     = 0.
        for person in self.group.infected_people():
            prob_transmission += person.transmission_probability(time)
        return prob_transmission

    def set_group(self,group):
        self.group = group
    
    def group(self):
        return self.group
    
class Interaction:
    def __init__(self,groups,time,mode="Probabilistic"):
        self.groups = groups
        self.time   = time
        self.mode   = mode
        for group in self.groups:
            group.update_status_lists(time)

    def single_time_step(self,time,infection_selector):
        for group in self.groups:
            interaction = Single_Interaction(group,self.mode)
            interaction.single_time_step(time,infection_selector)
