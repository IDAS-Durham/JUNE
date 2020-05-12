import random
import numpy as np
import yaml
from math import exp
from pathlib import Path
from june.interaction.interaction import Interaction

default_config_filename = (
    Path(__file__).parent.parent.parent
    / "configs/defaults/interaction/DefaultInteraction.yaml"
)

class DefaultInteraction(Interaction):

    def __init__(self, intensities):
        self.intensities = intensities

    @classmethod
    def from_file(
            cls, config_filename: str  = default_config_filename
    ) -> "DefaultInteraction":

        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        return DefaultInteraction(config['intensities'])

 
    def read_contact_matrix(self, group):
        #TODO use to intialize the different config matrices at the init,
        # ideally inside from_file
        pass
   
    def single_time_step_for_group(self, group, health_index_generator, time, delta_time):
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
        n_subgroups = len(group.subgroups)
        self.contact_matrix = np.ones((n_subgroups, n_subgroups))
        # Only need to iterate over sub-groups that contain people otherwise
        # we waste costly function calls n^2 times
        subgroups_containing_people = [
            x for x in range(n_subgroups) if group.subgroups[x].contains_people
        ]
        for i in subgroups_containing_people:
            for j in subgroups_containing_people:
                # grouping[i] infected infects grouping[j] susceptible
                self.contaminate(group, health_index_generator, time, delta_time, i,j)
                if i!=j:
                    # =grouping[j] infected infects grouping[i] susceptible
                    self.contaminate(group, health_index_generator, time, delta_time, j,i)

    def contaminate(self,group, health_index_generator, time, delta_time,  infecters,recipients):
        #TODO: subtitute by matrices read from file when ready
        contact_matrix = self.contact_matrix[infecters][recipients]
        infecter_probability = self.probabilities[infecters]
        if (
            contact_matrix <= 0. or
            infecter_probability <= 0.
        ):
            return

        intensity = (
            self.intensities.get(group.spec) * contact_matrix *
            infecter_probability * -delta_time
        )
        group_of_recipients = group.subgroups[recipients].people
        should_be_infected = np.random.random(len(group_of_recipients))
        for recipient, luck in zip(group_of_recipients, should_be_infected):
            transmission_probability = 1.0 - exp(
                recipient.health_information.susceptibility * intensity
            )
            if luck <= transmission_probability:
                infecter = self.select_infecter()
                infecter.health_information.infection.infect_person_at_time(
                    person=recipient, health_index_generator=health_index_generator, time=time,
                )
                infecter.health_information.increment_infected()
                recipient.health_information.update_infection_data(
                    time=time, group_type=group.spec
                )

    def calculate_probabilities(self, group):
        norm   = 1./max(1, group.size_active)
        for grouping in group.subgroups:
            summed = 0.
            for person in grouping.infected_active(group.spec):
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
