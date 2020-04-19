from covid.interaction import Interaction
from covid.infection import Infection
from covid.groups import Group
import numpy as np
import sys
import random


class InteractionCollective(Interaction):
    def __init__(self, user_parameters, world):
        self.world = world
        required_parameters = ["mode"]
        super().__init__(user_parameters, required_parameters)

    def single_time_step_for_group(self, group):
        if (
            group.size() <= 1
            or group.size_infected() == 0
            or group.size_susceptible() == 0
        ):
            return None
        infected_person = group.get_infected()[0]
        transmission_probability = self.calculate_transmission_probability(group)
        if transmission_probability <= 0.0:
            return
        for recipient in group.get_susceptible():
            self.single_time_step_for_recipient(
                infected_person, recipient, transmission_probability, group
            )

    def single_time_step_for_recipient(
        self, infecter, recipient, transmission_probability, group
    ):
        recipient_probability = recipient.get_susceptibility()
        if recipient_probability > 0.0:
            if random.random() <= transmission_probability * recipient_probability:
                # TODO fix this
                infecter.infection.infect(recipient)
                recipient.get_counter().update_infection_data(
                    self.world.timer.now, group.get_spec()
                )
                disc = random.random()
                i = 0
                while disc > 0.0 and i < len(self.weights) - 1:
                    i += 1
                self.weights[i][0].get_counter().increment_infected()

    def calculate_transmission_probability(self, group):
        transmission_probability = 0.0
        self.weights = []
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
        interaction_intensity = (
            group.get_intensity()
            / max(1, group.size() - 1)
            * (self.world.timer.now - self.world.timer.previous)
        )
        prob_notransmission = 1.0
        summed_prob = 0.0
        for person in group.get_infected():
            probability = max(
                0.0,
                1.0 - person.infection.transmission.probability * interaction_intensity,
            )
            prob_notransmission *= probability
            summed_prob += probability
            self.weights.append([person, probability])
        for i in range(len(self.weights)):
            self.weights[i][1] /= summed_prob
        return 1.0 - prob_notransmission

    def added_transmission_probability(self, group):
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
            probability = person.infection.transmission.probability
            prob_transmission += probability
            self.weights.append([person, probability])
        for i in range(len(self.weights)):
            self.weights[i][1] /= prob_transmission
        interaction_intensity = (
            group.get_intensity()
            / max(group.size() - 1, 1)
            * (self.world.timer.now - self.world.timer.previous)
        )
        return prob_transmission * interaction_intensity
