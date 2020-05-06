import random
import numpy as np
from interaction import Interaction

class DefaultInteraction(Interaction):
    def __init__(self):
        super().__init__()

    def single_time_step_for_group(self):
        if self.group.must_timestep():
            calculate_probabilties()
            for gi in group.groupings:
                for gj in group.groupings:
                    self.contaminate(self,i,j)
                    if i!=j:
                        self.contaminate(self,j,i)

    def contaminate(self,infecters,recipients):
        if (
            self.group.intensity[infecters][recipients] <= 0. or
            self.probabilities[infecters] <= 0.
        ):
            return
        for recipient in self.group.groupings[recipients]:
            transmission_probability = 1.0 - np.exp(
                -self.delta_t *
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
                    time=self.time, group_type=group.spec
                )

    def calculate_probabilities():
        self.probabilities = []
        for grouping in self.group.groupings:
            summed = 0.
            norm   = 1./max(1, self.grouping.size)
            for person in grouping.infected:
                individual = (
                    person.health_information.infection.transmission.probability
                )
                summed += individual*norm
                self.weights.append([person, individual])
            self.probabilities.append(summed) 

    def select_infecter(self):
        choice_weights = [w[1] for w in self.weights]
        idx = np.random.choice(range(len(self.weights)), 1, p=choice_weights)[0]
        return self.weights[idx][0]
