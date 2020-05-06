import random
import numpy as np
import yaml
from pathlib import Path
from covid.interaction.interaction import Interaction

default_config_filename = (
    Path(__file__).parent.parent.parent
    / "configs/defaults/interaction/DefaultInteraction.yaml"
)

class DefaultInteraction(Interaction):
    def __init__(self,intensities):
        """
        Default Interaction class, makes interactions between members of a group happen
        leading to infections

        Parameters
        ----------
        intensities:
            dictionary of intensities for the different
            group types
        """
        self.intensities = intensities

    @classmethod
    def from_file(
        cls, config_filename: str = default_config_filename
    ) -> "DefaultInteraction":
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return DefaultInteraction(config.get("intensities"))
    
    def single_time_step_for_group(self, group, time, delta_time):
        """
        Runs the interaction model for a time step
        Parameters
        ----------
        group:
            group to run the interaction on
        time:
            time at which the interaction starts to take place
        delta_time: 
            duration of the interaction 
        """

        if group.must_timestep:
            probabilities, weights = self.calculate_probabilities()
            for i in range(group.n_groupings):
                for j in range(group.n_groupings):
                    # grouping[i] infected infects grouping[j] susceptible
                    self.contaminate(group, time, probabilities, weights,i,j)
                    if i!=j:
                        # =grouping[j] infected infects grouping[i] susceptible
                        self.contaminate(group, time, probabilities, weights,j,i)

    def contaminate(self,group, time, delta_time, probabilities, weights, infecters,recipients):
        if (
            group.intensity[infecters][recipients] <= 0. or
            probabilities[infecters] <= 0.
        ):
            return
        for recipient in group.groupings[recipients]:
            transmission_probability = 1.0 - np.exp(
                -delta_time *
                recipient.health_information.susceptibility *
                group.intensity[infecters][recipients] *
                probabilities[infecters]
            )
            if random.random() <= transmission_probability:
                infecter = self.select_infecter(weights)
                infecter.health_information.infection.infect_person_at_time(
                    person=recipient, time=time
                )
                infecter.health_information.counter.increment_infected()
                recipient.health_information.counter.update_infection_data(
                    time=time, group_type=group.spec
                )

    def calculate_probabilities(self, group):
        for grouping in group.groupings:
            summed = 0.
            norm   = 1./max(1, grouping.size)
            for person in grouping.infected:
                individual = (
                    person.health_information.infection.transmission.probability
                )
                summed += individual*norm
                weights.append([person, individual])
            probabilities.append(summed)
            return probabilities, weights

    def select_infecter(self, weights):
        """
        Assign responsiblity to infecter for infecting someone
        """
        summed_weight = 0.
        for weight in weights:
            summed_weight += weight[1]
        choice_weights = [w[1]/summed_weight for w in weights]
        idx = np.random.choice(range(len(weights)), 1, p=choice_weights)[0]
        return weights[idx][0]
