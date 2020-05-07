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
        self.probabilities = []
        self.weights = []

        #if group.must_timestep:
        self.calculate_probabilities(group)
        for i in range(group.n_groupings):
            for j in range(group.n_groupings):
                # grouping[i] infected infects grouping[j] susceptible
                self.contaminate(group, time, delta_time, i,j)
                if i!=j:
                    # =grouping[j] infected infects grouping[i] susceptible
                    self.contaminate(group, time, delta_time, j,i)

    def contaminate(self,group, time, delta_time,  infecters,recipients):
        if (
            self.intensities.get(group.spec)[infecters][recipients] <= 0. or
            self.probabilities[infecters] <= 0.
        ):
            return
        for recipient in group.groupings[recipients]:
            transmission_probability = 1.0 - np.exp(
                -delta_time *
                recipient.health_information.susceptibility *
                self.intensities.get(group.spec)[infecters][recipients] *
                self.probabilities[infecters]
            )
            if random.random() <= transmission_probability:
                infecter = self.select_infecter()
                infecter.health_information.infection.infect_person_at_time(
                    person=recipient, time=time
                )
                infecter.health_information.increment_infected()
                recipient.health_information.update_infection_data(
                    time=time, group_type=group.spec
                )

    def calculate_probabilities(self, group):
        norm   = 1./max(1, group.size)
        for grouping in group.groupings:
            summed = 0.
            for person in grouping.infected:
                individual = (
                    person.health_information.infection.transmission.probability
                )
                summed += individual*norm
                self.weights.append([person, individual])
            self.probabilities.append(summed)

    def select_infecter(self):
        """
        Assign responsiblity to infecter for infecting someone
        """
        summed_weight = 0.
        for weight in self.weights:
            summed_weight += weight[1]
        choice_weights = [w[1]/summed_weight for w in self.weights]
        idx = np.random.choice(range(len(self.weights)), 1, p=choice_weights)[0]
        return self.weights[idx][0]
