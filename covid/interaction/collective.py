from covid.interaction import Interaction
from covid.infection import Infection
from covid.groups import Group
import numpy as np
import sys
import random


class InteractionCollective(Interaction):
    def __init__(self, user_parameters, world):
        required_parameters = ["mode"]
        super().__init__(user_parameters, required_parameters, world)
        self.alphas = {}

    def single_time_step_for_group(self, group):
        if (
            group.size <= 1
            or group.size_infected == 0
            or group.size_susceptible == 0
        ):
            return None
        effective_load = self.calculate_effective_viral_load(group)
        if effective_load <= 0.: #TODO ask Frank
            return
        for recipient in group.susceptible:
            self.single_time_step_for_recipient(
                recipient, effective_load, group
            )

    def single_time_step_for_recipient(
        self, recipient, effective_load, group
    ):
        transmission_probability  = 0.
        recipient_probability     = recipient.susceptibility
        if recipient_probability <= 0.0:
            return
        if self.mode == "superposition":
            """
            added probability from product of non-infection probabilities.
            for each time step, the infection probabilities per infected person are given
            by their individual, time-dependent infection probability times the
            interaction intensity normalised to the group size --- this is to recover the
            logic of the SI/SIR models --- and normalised to the time interval, given in
            units of full days.
            """
            transmission_probability = recipient_probability * effective_load
        elif self.mode == "probabilistic":
            """
            multiplicative probability from product of non-infection probabilities.
            for each time step, the infection probabilities per infected person are given
            by their individual, time-dependent infection probability times the
            interaction intensity normalised to the group size --- this is to recover the
            logic of the SI/SIR models --- and normalised to the time interval, given in
            units of full days.
            """
            transmission_probability = 1.-np.exp(recipient_probability * effective_load)
        if random.random() <= transmission_probability:
            infecter = self.select_infecter()
            infecter.infection.infect(recipient)
            infecter.counter.increment_infected()
            recipient.counter.update_infection_data(
                self.world.timer.now, group.spec
            )

    def calculate_effective_viral_load(self, group):
        grouptype = group.spec
        summed_load = 0.0
        interaction_intensity = (
            self.get_intensity(grouptype) /
            (max(1, group.size)**self.get_alpha(grouptype)) *
            (self.world.timer.now - self.world.timer.previous)
        )
        if interaction_intensity > 0.:
            self.weights = []
            for person in group.infected:
                viral_load   = person.infection.transmission.transmission_probability
                summed_load += viral_load
                self.weights.append([person, viral_load])
            for i in range(len(self.weights)):
                self.weights[i][1] /= summed_load
            summed_load *= interaction_intensity
        return summed_load

    def select_infecter(self):
        disc = random.random()
        i    = 0
        while disc > 0.0 and i < len(self.weights)-1:
            i += 1
        return self.weights[i][0]

    def get_alpha(self,grouptype):
        if grouptype in self.alphas:
            return self.alphas[grouptype]
        return 1.

    def set_alphas(self,alphas):
        self.alphas = alphas

    def set_alpha(self,grouptype,alpha):
        self.alphas[grouptype] = alpha
        
