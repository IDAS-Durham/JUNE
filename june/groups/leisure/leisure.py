import numpy as np
from numba import jit
from typing import List
from june.demography import Person
from june.groups.leisure import SocialVenueDistributor


@jit(nopython=True)
def roll_poisson_dice(poisson_parameter, delta_time):
    return np.random.rand() < (1.0 - np.exp(-poisson_parameter * delta_time))


class Leisure:
    """
    Class to manage all possible activites that happen during leisure time.
    """
    def __init__(self, leisure_distributors: List[SocialVenueDistributor]):
        """
        Parameters
        ----------
        leisure_distributors
            List of social venue distributors.
        """
        self.leisure_distributors = leisure_distributors

    def get_leisure_distributor_for_person(
        self, person: Person, delta_time: float, is_weekend: bool = False
    ):
        """
        Given a person, reads its characteristics, and the amount of free time it has,
        and computes all poisson parameters for the different distributors.
        It then samples from a combined exponential distribution,
        1 - np.exp(- sum(lambda) * delta_t)
        to decide whether an activity happens.
        Another sampling with the relative weights of the poisson parameters
        decides which exact activity takes place.

        Parameters
        ----------
        person
            an instance of Person with age and sex defined.
        delta_time
            the amount of time for leisure
        is_weekend
            whether it is a weekend or not
        """
        poisson_parameters = []
        for distributor in self.leisure_distributors:
            poisson_parameters.append(
                distributor.get_poisson_parameter(person, is_weekend)
            )
        total_poisson_parameter = np.sum(poisson_parameters)
        does_activity = roll_poisson_dice(total_poisson_parameter, delta_time)
        if does_activity is False:
            return
        poisson_parameters_normalized = np.array(poisson_parameters) / np.sum(
            poisson_parameters
        )
        which_activity = np.random.choice(
            np.arange(0, len(poisson_parameters)), p=poisson_parameters_normalized
        )
        return self.leisure_distributors[which_activity]

    def assign_social_venue_to_person(self, person, leisure_distributor):
        social_venue = leisure_distributor.get_social_venue_for_person(person)
        social_venue.add(person)
        return social_venue

    def send_household_with_person_if_necessary(self, person, leisure_distributor, social_venue):
        """
        When we know that the person does an activity in the social venue X,
        then we ask X whether the person needs to drag the household with 
        him or her.
        """
        person_residence = person.subgroups[person.ActivityType.residence].group
        if person_residence.spec == "care_home" or person_residence.communal:
            return False
        if leisure_distributor.person_drags_household():
            for mate in person.housemates:
                social_venue.add(mate) # ignores size checking
            return True


