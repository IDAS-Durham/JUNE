import random
import numpy as np
import yaml
from pathlib import Path

collective_default_config_filename = (
    Path(__file__).parent.parent.parent
    / "configs/defaults/interaction/InteractionCollective.yaml"
)


class Interaction:
    def __init__(self, intensities: dict):
        """
        Interaction class, makes interactions between members of a group happen
        leading to infections

        Parameters
        ----------

        intensities:
            dictionary of intensities for the different
            group types
        """
        self.intensities = intensities

    def time_step(self, time: float, delta_time: float, group: "Group"):
        """
        Runs the interaction model for a time step

        Parameters
        ----------

        time:
            time at which the
        delta_time: 
            duration of the timestep
        group:
            group to run the interaction on
        """

        self.single_time_step_for_group(group=group, time=time, delta_time=delta_time)
        group.update_status_lists(time=time, delta_time=delta_time)


class InteractionCollective(Interaction):
    def __init__(self, mode: str, intensities: dict):
        """
        Define an interaction model where probabilities are combined

        Parameters
        ---------
        mode:
            mode of interatio. Either probabilistic or 
        intensities:
            dictionary with group intensities depending on group type
        """
        super().__init__(intensities)
        self.mode = mode
        self.alphas = {}

    @classmethod
    def from_file(
        cls, config_filename: str = collective_default_config_filename
    ) -> "InteractionCollective":
        """
        Initialize Hospitals from path to data frame, and path to config file 

        Parameters
        ----------
        filename:
            path to hospital dataframe
        config_filename:
            path to hospital config dictionary
        Returns
        -------
        Interaction instance
        """

        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return InteractionCollective(config.get("mode"), config.get("intensities"))

    def single_time_step_for_group(
        self, group: "Group", time: float, delta_time: float
    ):
        """
        Runs the interaction model for a time step

        Parameters
        ----------
        group:
            group to run the interaction on
        time:
            time at which the
        delta_time: 
            duration of the timestep
        """

        if group.must_timestep:

            effective_load = self.calculate_effective_viral_load(group, delta_time)

            if effective_load <= 0.0:
                return

            for recipient in group.susceptible:
                self.single_time_step_for_recipient(
                    recipient=recipient,
                    effective_load=effective_load,
                    group=group,
                    time=time,
                )

        # TODO: must allow for infection of workers by patients

    def single_time_step_for_recipient(
        self, recipient: "Person", effective_load: float, group: "Group", time: float
    ):
        """
        Run the interaction time step for a recipient of the interaction

        Parameters
        ----------
        recipient:
            person susceptible to be infected
        effective_load:
            combined probability of all the infected people in the group during the whole time step to infect recipient
        group:
            group in which to run the interaction
        time:
            time at which the interaction happens
        """

        transmission_probability = 0.0

        if recipient.health_information.susceptibility <= 0.0:
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
            transmission_probability = (
                recipient.health_information.susceptibility * effective_load
            )
        elif self.mode == "probabilistic":
            """
            multiplicative probability from product of non-infection probabilities.
            for each time step, the infection probabilities per infected person are given
            by their individual, time-dependent infection probability times the
            interaction intensity normalised to the group size --- this is to recover the
            logic of the SI/SIR models --- and normalised to the time interval, given in
            units of full days.
            """
            transmission_probability = 1.0 - np.exp(
                -recipient.health_information.susceptibility * effective_load
            )

        if random.random() <= transmission_probability:

            infecter = self.select_infecter()

            infecter.health_information.infection.infect_person_at_time(
                person=recipient, time=time
            )

            infecter.health_information.counter.increment_infected()

            recipient.health_information.counter.update_infection_data(
                time=time, group_type=group.spec
            )

    def calculate_effective_viral_load(self, group: "Group", delta_time: float):
        """
        Calculate the combined effect of all infected people over a time step
        to infect the susceptible people in the group

        Parameters
        ---------
        group:
            group over which to compute the viral load
        delta_time:
            duration of the time step
        """

        group_type = group.spec
        summed_load = 0.0
        interaction_intensity = (
            self.intensities.get(group_type)
            / (max(1, group.size) ** self.get_alpha(group_type=group_type))
            * (delta_time)
        )

        if interaction_intensity > 0.0:

            self.weights = []

            for person in group.infected:

                viral_load = (
                    person.health_information.infection.transmission.probability
                )
                summed_load += viral_load
                self.weights.append([person, viral_load])

            for i in range(len(self.weights)):

                self.weights[i][1] /= summed_load

            summed_load *= interaction_intensity

        return summed_load

    def select_infecter(self):
        """
        Assign responsiblity to infecter for infecting someone

        """

        choice_weights = [w[1] for w in self.weights]

        idx = np.random.choice(range(len(self.weights)), 1, p=choice_weights)[0]

        return self.weights[idx][0]

    #TODO: Comes from IC, but do we want to get rid off it?
    def get_alpha(self, group_type):

        if group_type in self.alphas:
            return self.alphas[group_type]

        return 1.0

    def set_alphas(self, alphas):

        self.alphas = alphas

    def set_alpha_of_group_type(self, group_type, alpha):

        self.alphas[group_type] = alpha


# TODO: ALL THIS NEEDS TO BE REFACTORED, NOT WORKING AT THE MOMENT
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
                    self.make_interactions(
                        time=time, infecter=infecter, group=group, age=age
                    )

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
            n_average = self.contacts[infecter.age]
            # find column infecter, and sum
            N_contacts = self.calculate_actual_N_contacts(n_average)
            draw_contacts = np.random.rand(N_contacts)
            contact_ages = np.searchsorted(
                self.probability[:, infecter.age], draw_contacts
            )
            for i in range(N_contacts):
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
            n_average = self.contacts[infecter.age]
            # find column infecter, and sum
            N_contacts = self.calculate_actual_N_contacts(n_average)
            draw_contacts = np.random.rand(N_contacts)
            contact_ages = np.searchsorted(
                self.probability[:, infecter.age], draw_contacts
            )
            for i in range(N_contacts):
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
            n_average = self.contacts[infecter.age]
            # find column infecter, and sum
            N_contacts = self.calculate_actual_N_contacts(n_average)
            draw_contacts = np.random.rand(N_contacts)
            contact_ages = np.searchsorted(
                self.probability[:, infecter.age], draw_contacts
            )
            for i in range(N_contacts):
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

    def calculate_actual_N_contacts(self, Nave):
        N = np.random.poisson(Nave)
        Nint = int(N)
        Nover = N - Nint
        if np.random.random() < Nover:
            Nint += 1
        return Nint
