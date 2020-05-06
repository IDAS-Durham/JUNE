import random
import numpy as np


class Interaction:
    def __init__(self,parameters=None):
        pass
        
    def time_step(self, time, delta_time, groups):
        # TODO : Is there any reason for this to be passed all groups, as opposed to one group at a time?
        # TODO : If not, make the class assume it always acts on one group (which could have sub groups internally).

        # TODO think how we treat the double update_status_lists and make it consistent
        # with delta_time
        
        self.time       = time
        self.delta_time = delta_time
        for group_type in groups:
            for self.group in group_type.members:
                if self.group.size != 0:
                    self.group.update_status_lists(time=self.time, delta_time=0)
                    self.single_time_step_for_group()
                    self.group.update_status_lists(time=self.time, delta_time=self.delta_time)
                    
    def single_time_step_for_group(self):
        raise NotImplementedError()

    
    
class InteractionCollective(Interaction):
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

    def calculate_loads():
        self.probabilities = []
        norm               = 1./max(1, self.group.size)
        #TODO: add back this scaling exponent if you need to but make it
        #      part of the group information.
        #      **self.get_alpha(group_type=group_type))
        for grouping in self.group.groupings:
            summed = 0.
            for person in grouping.infected:
                individual = (
                    person.health_information.infection.transmission.probability
                )
                summed += individual
                self.weights.append([person, individual])
            self.probabilities.append(summed*norm) 

    def select_infecter(self):
        choice_weights = [w[1] for w in self.weights]
        idx = np.random.choice(range(len(self.weights)), 1, p=choice_weights)[0]
        return self.weights[idx][0]

# TODO: READ MAX AGE (100) FROM SOMEWHERE
class MatrixInteraction(Interaction):
    """
    We assume that the matrices are symmetric, with age indexing rows and
    columns, and that they are organised in a dictionary with the group_type
    as key.  The sum over a row then gives th total number of interactions
    a person of a given age has per day in this group (we can vary this
    number on a daily base with a Poissonian distribution) - if we call
    each group only once per day, this translates immediately into contacts
    per call.  The resulting number of interactions is then distributed
    over group members according to the frequency in the matrix.
    """

    def __init__(self):
        super().__init__()

    def single_time_step_for_group(self, time, group):
        if group.must_timestep():

            self.matrix = group.get_contact_matrix()
            self.matrix = self.reduce_matrix(group)
            self.contacts, self.probability = self.normalize_contact_matrix(self.matrix)

            for infecter in group.get_infected():
                contact_ages = self.prepare_interaction_ages(infecter, group)
                for age in contact_ages:
                    self.make_interactions(time=time, infecter=infecter, group=group, age=age)

        if group.spec == "hospital":
            print("must allow for infection of workers by patients")

    def make_interactions(self, time, infecter, group, age):
        # randomly select someone with that age
        recipient = self.make_single_contact(infecter, group, age)
        if (
            recipient
            and not (recipient.is_infected())
            and recipient.susceptibility > 0.0
        ):
            if random.random() <= 1.0 - np.exp(
                -self.transmission_probability * recipient.susceptibility()
            ):
                infecter.infection.infect_person_at_time(person=recipient, time=time)
                recipient.counter.update_infection_data(
                    time=time, group_type=group.get_spec()
                )
                infecter.counter.increment_infected()

    def prepare_interaction_ages(self, delta_time, time, infecter, group):
        self.transmission_probability = self.calculate_single_transmission_probability(
            delta_time=delta_time, infecter=infecter, group=group
        )
        if self.transmission_probability > 1.0e-12:
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
                        -self.transmission_probability * recipient.susceptibility()
                    ):
                        infecter.infection.infect_person_at_time(recipient)
                        recipient.counter.update_infection_data(
                            time=time, group_type=group.get_spec()
                        )
                        infecter.counter.increment_infected()

    def calculate_single_transmission_probability(self, delta_time, infecter, group):
        intensity = group.intensity
        probability = infecter.infection.transmission.probability
        # probability *= self.severity_multiplier(group.get_spec())
        return probability * intensity * delta_time

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
