import numpy as np
from numba import jit
from typing import List
from june.demography import Person
from june.demography.geography import Geography
from june.groups.leisure import (
    SocialVenueDistributor,
    PubDistributor,
    GroceryDistributor,
    CinemaDistributor,
    VisitsDistributor,
)
from june.groups.leisure import Pubs, Cinemas, Groceries


@jit(nopython=True)
def random_choice_numba(arr, prob):
    """
    Fast implementation of np.random.choice
    """
    return arr[np.searchsorted(np.cumsum(prob), np.random.rand(), side="right")]


@jit(nopython=True)
def roll_activity_dice(poisson_parameters, delta_time, n_activities):
    total_poisson_parameter = np.sum(poisson_parameters)
    does_activity = np.random.rand() < (
        1.0 - np.exp(-total_poisson_parameter * delta_time)
    )
    if does_activity == False:
        return None
    else:
        poisson_parameters_normalized = poisson_parameters / total_poisson_parameter
        return random_choice_numba(
            np.arange(0, n_activities), poisson_parameters_normalized
        )


def generate_leisure_for_world(list_of_leisure_groups, world):
    """
    Generates an instance of the leisure class for the specified geography and leisure groups.

    Parameters
    ----------
    list_of_leisure_groups
        list of names of the lesire groups desired. Ex: ["pubs", "cinemas"]
    """
    leisure_distributors = []
    if "pubs" in list_of_leisure_groups:
        if not hasattr(world, "pubs"):
            raise ValueError("Your world does not have pubs.")
        leisure_distributors.append(PubDistributor.from_config(world.pubs))
    if "cinemas" in list_of_leisure_groups:
        if not hasattr(world, "cinemas"):
            raise ValueError("Your world does not have cinemas.")
        leisure_distributors.append(CinemaDistributor.from_config(world.cinemas))
    if "groceries" in list_of_leisure_groups:
        if not hasattr(world, "groceries"):
            raise ValueError("Your world does not have groceries.")
        leisure_distributors.append(GroceryDistributor.from_config(world.groceries))

    if "residence_visits" in list_of_leisure_groups:
        if not hasattr(world, "households") or not hasattr(world, "care_homes"):
            raise ValueError("Your world does not have households or care homes.")
        leisure_distributors.append(VisitsDistributor.from_config(world.super_areas))

    return Leisure(leisure_distributors)


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
        self.n_activities = len(self.leisure_distributors)

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
        activity = roll_activity_dice(
            np.array(poisson_parameters, dtype=np.float), delta_time, self.n_activities
        )
        if activity is None:
            return
        else:
            return self.leisure_distributors[activity]

    def assign_social_venue_to_person(self, person, leisure_distributor):
        social_venue = leisure_distributor.get_social_venue_for_person(person)
        social_venue.add(person, activity="leisure")
        return social_venue

    def send_household_with_person_if_necessary(
        self, person, leisure_distributor, social_venue
    ):
        """
        When we know that the person does an activity in the social venue X,
        then we ask X whether the person needs to drag the household with 
        him or her.
        """
        if (
            person.residence.group.spec == "care_home"
            or person.residence.group.type == "communal"
        ):
            return False
        if leisure_distributor.person_drags_household():
            for mate in person.residence.group.residents:
                if not mate.busy:
                    social_venue.add(mate, activity="leisure")  # ignores size checking
            return True

    def get_subgroup_for_person_and_housemates(
        self, person: Person, delta_time: float, is_weekend: bool
    ):
        """
        Main function of the Leisure class. For every possible activity a person can do,
        we chech the Poisson parameter lambda = probability / day * deltat of that activty 
        taking place. We then sum up the Poisson parameters to decide whether a person
        does any activity at all. The relative weight of the Poisson parameters gives then
        the specific activity a person does. 
        If a person ends up going to a social venue, we do a second check to see if his/her
        entire household accompanies him/her.
        The social venue subgroups are attached to the involved people, but they are not 
        added to the subgroups, since it is possible they change their plans if a policy is in
        place or they have other responsibilities.
        The function returns None if no activity takes place.

        Parameters
        ----------
        person
            an instance of person
        delta_time
            the time someone has for leisure
        is_weekend
            whether it is a weekend or not
        """
        social_venue_distributor = self.get_leisure_distributor_for_person(
            person, delta_time, is_weekend
        )
        if social_venue_distributor is None:
            return None
        social_venue = self.assign_social_venue_to_person(
            person=person, leisure_distributor=social_venue_distributor
        )
        self.send_household_with_person_if_necessary(
            person=person,
            leisure_distributor=social_venue_distributor,
            social_venue=social_venue,
        )
        return person.leisure
