import random
import numpy as np
from interaction import Interaction

class DefaultInteraction(Interaction):
    def __init__(self):
        super().__init__()
        print("initialized default interaction model.")

    def single_time_step_for_group(self):
        self.probabilities = []
        self.weights       = []
        if self.group.must_timestep():
            self.calculate_probabilities()
            for i in range(self.group.n_groupings):
                for j in range(self.group.n_groupings):
                    # grouping[i] infects grouping[j]
                    self.contaminate(i,j)
                    if i!=j:
                        # =grouping[j] infects grouping[i]
                        self.contaminate(j,i)

    def contaminate(self,infecters,recipients):
        if (
            self.group.intensity[infecters][recipients] <= 0. or
            self.probabilities[infecters] <= 0.
        ):
            return
        for recipient in self.group.groupings[recipients]:
            transmission_probability = 1.0 - np.exp(
                -self.delta_time *
                recipient.health_information.susceptibility *
                self.group.intensity[infecters][recipients] *
                self.probabilities[infecters]
            )
            if random.random() <= transmission_probability:
                infecter = self.select_infecter()
                infecter.health_information.infection.infect_person_at_time(
                    person=recipient, time=self.time
                )
                infecter.health_information.counter.increment_infected()
                recipient.health_information.counter.update_infection_data(
                    time=self.time, group_type=self.group.spec
                )

    def calculate_probabilities(self):
        for grouping in self.group.groupings:
            summed = 0.
            norm   = 1./max(1, grouping.size)
            for person in grouping.infected:
                individual = (
                    person.health_information.infection.transmission.probability
                )
                summed += individual*norm
                self.weights.append([person, individual])
            self.probabilities.append(summed)

    def select_infecter(self):
        summed_weight = 0.
        for weight in self.weights:
            summed_weight += weight[1]
        choice_weights = [w[1]/summed_weight for w in self.weights]
        idx = np.random.choice(range(len(self.weights)), 1, p=choice_weights)[0]
        return self.weights[idx][0]
