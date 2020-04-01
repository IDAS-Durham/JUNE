import infection as Infection
import group     as Group 
import person    as Person
import sys
import random

class Single_Interaction:
    def __init__(self,group):
        if not isinstance(group,Group.Group):
            print ("Error in Interaction.__init__, no group:",group)
            return
        self.group = group
        
    def single_time_step(self,time,infection_selector):
        if (self.group.size_infected() == 0 or self.group.size_healthy() == 0): 
            return
        for person in self.group.healthy_people():
            transmission_probability = self.combined_transmission_probability(person,time)
            print ("Testing ",person.name())
            if random.random() < transmission_probability:
                print (*"Person ",person.name()," is now infected.")
                person.set_infection(infection_selector.make_infection(time))
                
    def combined_transmission_probability(self,recipient,time):
        susceptibility        = recipient.susceptibility()
        interaction_intensity = self.group.intensity()
        recipient_probability = susceptibility * interaction_intensity
        prob_notransmission   = 1.
        for person in self.group.infected_people():
            individual_prob      = (person.transmission_probability(time) *
                                    recipient_probability)
            prob_notransmission *= (1.-individual_prob)
        return 1.-prob_notransmission
                
    def set_group(self,group):
        self.group = group
    
    def group(self):
        return self.group
        


    
class Interaction:
    def __init__(self,groups,time):
        self.groups = groups
        self.time   = time
        for group in self.groups:
            group.update_status_lists(time)

    def single_time_step(self,time,infection_selector):
        for group in groups:
            interaction = single_interaction(group)
            interaction.single_time_step(time,infection_selector)
