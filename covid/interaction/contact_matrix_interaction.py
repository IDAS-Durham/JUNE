from covid.interaction import Interaction
from covid.infection import Infection
from covid.groups import Group
from covid.world import World
import numpy as np
import sys
import random

"""
We assume that the matrices are symmetric, with age indexing rows and
columns, and that they are organised in a dictionary with the grouptype
as key.  The sum over a row then gives th total number of interactions
a person of a given age has per day in this group (we can vary this
number on a daily base with a Poissonian distribution) - if we call
each group only once per day, this translates immediately into contacts
per call.  The resulting number of interactions is then distributed
over group members according to the frequency in the matrix.
"""


# TODO: READ MAX AGE (100) FROM SOMEWHERE
class MatrixInteraction(Interaction):
    def __init__(self, world, user_parameters={}):
        self.world = world
        required_parameters = []
        super().__init__(user_parameters, required_parameters)

    def single_time_step_for_group(self, group):
        if (
            group.size <= 1
            or group.size_infected() == 0
            or group.size_susceptible() == 0
        ):
            return

        self.matrix = group.get_contact_matrix()
        self.matrix = self.reduce_matrix(group)
        self.contacts, self.probability = self.normalize_contact_matrix(self.matrix)

        for infecter in group.get_infected():
            transmission_probability = self.calculate_single_transmission_probability(
                infecter, group
            )
            Naverage = self.contacts[infecter.age]
            # find column infecter, and sum
            Ncontacts = self.calculate_actual_Ncontacts(Naverage)
            draw_contacts = np.random.rand(Ncontacts)
            contact_ages = np.searchsorted(
                self.probability[:, infecter.age], draw_contacts
            )
            for i in range(Ncontacts):
                # randomly select someone with that age
                recipient = self.make_single_contact(infecter, group, contact_ages[i])
                if recipient and (
                    not (recipient.is_infected()) and recipient.susceptibility > 0.0
                ):
                    if random.random() <= 1.0 - np.exp(
                        -transmission_probability * recipient.susceptibility()
                    ):
                        infecter.infection.infect(recipient)
                        recipient.counter.update_infection_data(
                            self.world.timer.now, group.get_spec()
                        )
                        infecter.counter.increment_infected()

    def calculate_single_transmission_probability(self, infecter, group):
        intensity = group.get_intensity(self.time)
        probability = infecter.transmission.transmission_probability
        # probability *= self.severity_multiplier(group.get_spec())
        return (
            probability * intensity * (self.world.timer.now - self.world.timer.before)
        )

    def test_single_time_step_for_group(self, group):

        self.test_matrix = np.zeros((100, 100))
        self.matrix = group.get_contact_matrix()
        people = group.get_people()

        self.matrix = self.reduce_matrix(group)
        self.contacts, self.probability = self.normalize_contact_matrix(self.matrix)

        for infecter in people:
            Naverage = self.contacts[infecter.age]
            # find column infecter, and sum
            Ncontacts = self.calculate_actual_Ncontacts(Naverage)
            draw_contacts = np.random.rand(Ncontacts)
            contact_ages = np.searchsorted(
                self.probability[:, infecter.age], draw_contacts
            )
            for i in range(Ncontacts):
                # randomly select someone with that age
                recipient = self.make_single_contact(infecter, group, contact_ages[i])
                if recipient:
                    self.test_matrix[infecter.age][recipient.age] += 1 / 2
                    self.test_matrix[recipient.age][infecter.age] += 1 / 2

    def test_single_time_step_for_group(self, group):

        self.matrix = group.get_contact_matrix()
        people = group.get_people()

        self.matrix = self.reduce_matrix(group)
        self.contacts, self.probability = self.normalize_contact_matrix(self.matrix)

        for infecter in people:
            Naverage = self.contacts[infecter.age]
            # find column infecter, and sum
            Ncontacts = self.calculate_actual_Ncontacts(Naverage)
            draw_contacts = np.random.rand(Ncontacts)
            contact_ages = np.searchsorted(
                self.probability[:, infecter.age], draw_contacts
            )
            for i in range(Ncontacts):
                # randomly select someone with that age
                recipient = self.make_single_contact(infecter, group, contact_ages[i])
                if recipient:
                    self.test_matrix[infecter.age][recipient.age] += 1 / 2
                    self.test_matrix[recipient.age][infecter.age] += 1 / 2

    def reduce_matrix(self, group):
        # Find empty ages
        matrix = group.get_contact_matrix()
        not_in_group = np.setxor1d(
            np.arange(len(matrix)), [person.age for person in group.people]
        )
        # if no age empty
        if len(not_in_group) == 0:
            return matrix
        else:
            return self.remove_distribute_matrix(matrix, not_in_group)

    def remove_distribute_matrix(self, matrix, to_remove):
        # Redistribute values of those bins
        contacts_to_share = matrix[to_remove, :].sum(axis=0)
        reduced_matrix = matrix.copy()
        reduced_matrix[to_remove, :] = np.zeros((len(to_remove), len(matrix)))
        reduced_matrix[:, to_remove] = np.zeros((len(matrix), len(to_remove)))
        weights = np.nan_to_num(reduced_matrix / reduced_matrix.sum(axis=0))
        reduced_matrix += contacts_to_share * weights
        return reduced_matrix

    def normalize_contact_matrix(self, matrix):
        mean_contacts = matrix.sum(axis=0)
        probability = matrix / mean_contacts
        return mean_contacts, np.cumsum(probability, axis=0)

    def make_single_contact(self, infecter, group, contact_age):
        # TODO: Think about implications for very small groups, this will lower the number of interactions
        if infecter.age == contact_age and len(group.age_pool[contact_age]) == 1:
            return None
        recipient = infecter
        while recipient == infecter:
            recipient = np.random.choice(group.age_pool[contact_age])
        return recipient

    def calculate_actual_Ncontacts(self, Nave):
        N = np.random.poisson(Nave)
        Nint = int(N)
        Nover = N - Nint
        if np.random.random() < Nover:
            Nint += 1
        return Nint


if __name__ == "__main__":
    world = World()
    mi = MatrixInteraction(world)
    mi.single_time_step_for_group(world.households.members[0])
