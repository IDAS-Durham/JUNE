from math import exp

import numpy as np
import yaml

from june import paths
from june.interaction.interaction import Interaction

default_config_filename = (
        paths.configs_path
        / "defaults/interaction/DefaultInteraction.yaml"
)


class DefaultInteraction(Interaction):
    def __init__(self, alpha_physical, contact_matrices, selector=None):
        self.contacts = {}
        self.physical = {}
        self.beta     = {}
        self.alpha    = alpha_physical
        self.schoolC  = 2.50
        self.schoolP  = 0.15
        self.schoolxi = 0.30
        self.selector = selector
        for tag in contact_matrices.keys():
            self.fix_group_matrices(tag, contact_matrices)

    def fix_group_matrices(self, tag, contact_matrices):
        self.beta[tag] = 1.0
        self.contacts[tag] = [[1.0]]
        self.physical[tag] = [[0.0]]
        if tag in contact_matrices:
            if "beta" in contact_matrices[tag]:
                self.beta[tag] = contact_matrices[tag]["beta"]
            if "contacts" in contact_matrices[tag]:
                self.contacts[tag] = contact_matrices[tag]["contacts"]
            if "physical" in contact_matrices[tag]:
                self.physical[tag] = contact_matrices[tag]["physical"]
        elif tag == "school":
            if "xi" in contact_matrices[tag]:
                self.schoolxi = float(contact_matrices[tag]["xi"])
            if len(self.contacts["school"]) == 2 and len(self.physical["school"]) == 2:
                self.schoolC = float(self.contacts["school"][1][1])
                self.schoolP = float(self.physical["school"][1][1])

    @classmethod
    def from_file(
            cls,
            config_filename: str = default_config_filename
    ) -> "DefaultInteraction":

        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        return DefaultInteraction(config["alpha_physical"], config["contact_matrices"])

    def single_time_step_for_group(
            self, group, time, delta_time
    ):
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

        # if group.must_timestep:
        self.calculate_probabilities(group)
        n_subgroups = len(group.subgroups)
        # Only need to iterate over sub-groups that contain people otherwise
        # we waste costly function calls n^2 times
        subgroups_containing_people = [
            x for x in range(n_subgroups) if group.subgroups[x].contains_people
        ]
        for i in subgroups_containing_people:
            for j in subgroups_containing_people:
                # grouping[i] infected infects grouping[j] susceptible
                self.contaminate(group, time, delta_time, i, j)
                if i != j:
                    # grouping[j] infected infects grouping[i] susceptible
                    self.contaminate(group, time, delta_time, j, i)

    def contaminate(
            self, group, time, delta_time, infecters, recipients
    ):
        # TODO: subtitute by matrices read from file when ready
        infecter_probability = self.probabilities[infecters]
        if infecter_probability <= 0.0:
            return

        intensity = (
            self.intensity(group, infecters, recipients) *
            infecter_probability
        )
        group_of_recipients = group.subgroups[recipients].people
        should_be_infected  = np.random.random(len(group_of_recipients))
        for recipient, luck in zip(group_of_recipients, should_be_infected):
            transmission_probability = 1.0 - exp(
                - delta_ime * recipient.health_information.susceptibility * intensity
            )
            if luck <= transmission_probability:
                infecter = self.select_infecter()
                infecter.health_information.infection.infect_person_at_time(
                    selector = self.selector,
                    person   = recipient,
                    time     = time,
                )
                infecter.health_information.increment_infected()
                recipient.health_information.update_infection_data(
                    time=time, group_type=group.spec
                )

    def intensity(self, group, infecter, recipient):
        tag = group.spec
        if tag == "school":
            if infecter > 0 and recipient > 0:
                delta = pow(self.schoolxi, abs(recipient - infecter))
                mixer = self.schoolC * delta
                phys  = self.schoolP * delta
            elif infecter == 0 and recipient > 0:
                mixer = self.contacts[tag][1][0]
                phys  = self.physical[tag][1][0]
            elif infecter > 0 and recipient == 0:
                mixer = self.contacts[tag][0][1]
                phys  = self.physical[tag][0][1]
            else:
                mixer = self.contacts[tag][0][0]
                phys  = self.physical[tag][0][0]
        else:
            if recipient >= len(self.contacts[tag]) or infecter >= len(
                    self.contacts[tag][recipient]
            ):
                mixer = 1.0
                phys  = 0.0
            else:
                mixer = self.contacts[tag][recipient][infecter]
                phys = self.physical[tag][recipient][infecter]
        if tag == "commute_Public":
            # get the location-dependent group modifiers here,
            # they will take into account intensity and physicality
            # of the interaction by modifying mixer and phys.
            mixer *= 1.0
            phys  *= 1.0
        return self.beta[tag] * float(mixer) * (1.0 + (self.alpha - 1.0) * float(phys))

    def calculate_probabilities(self, group):
        norm = 1.0 / max(1, group.size_active)
        for grouping in group.subgroups:
            summed = 0.0
            for person in grouping.infected_active(group.spec):
                individual = (
                    person.health_information.infection.transmission.probability
                )
                summed += individual * norm
                self.weights.append([person, individual])
            self.probabilities.append(summed)

    def select_infecter(self):
        """
        Assign responsiblity to infecter for infecting someone
        """
        summed_weight = 0.0
        for weight in self.weights:
            summed_weight += weight[1]
        choice_weights = [w[1] / summed_weight for w in self.weights]
        idx = np.random.choice(range(len(self.weights)), 1, p=choice_weights)[0]
        return self.weights[idx][0]
