from covid.interaction import Interaction
from covid.infection import Infection
from covid.groups import Group
import numpy as np
import sys
import random


class CollectiveInteraction(Interaction):
    
    def init(self):
        if "probmode" in self.params:
            self.mode = self.params["probmode"]
            if self.mode != "superposition" and self.mode != "probabilistic":
                print ("CollectiveInteraction model with illegal mode", self.mode)
                print ("--> will move to 'Superposition'")
                self.mode = "superposition"
        else:
                self.mode = "superposition"
        
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
        if self.mode == "superposition":
            transmission_probability = self.added_transmission_probability(group)
        elif self.mode == "probabilistic":
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
                max(0., 1.0 - person.transmission_probability(self.time) * interaction_intensity)
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
        prob_transmission = 0.0
        for person in group.get_infected():
            prob_transmission += person.transmission_probability(self.time)
        interaction_intensity = group.get_intensity() / max(group.size()-1,1) * self.delta_t
        return prob_transmission * interaction_intensity
