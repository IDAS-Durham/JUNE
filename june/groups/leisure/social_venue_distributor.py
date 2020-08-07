import numpy as np
from typing import List
from numba import jit
from numba import typed
from itertools import chain
import re

from june.groups.leisure import SocialVenues, SocialVenue, SocialVenueError
from june.groups import Household
from june.utils.parse_probabilities import parse_age_probabilities


@jit(nopython=True)
def random_choice_numba(arr, prob):
    """
    Fast implementation of np.random.choice
    """
    return arr[np.searchsorted(np.cumsum(prob), np.random.rand(), side="right")]



class SocialVenueDistributor:
    """
    Tool to associate social venues to people.
    """

    def __init__(
        self,
        social_venues: SocialVenues,
        male_age_probabilities: dict = None,
        female_age_probabilities: dict = None,
        drags_household_probability=0.5,
        neighbours_to_consider=5,
        maximum_distance=5,
        weekend_boost: float = 1.0,
    ):
        """
        A sex/age profile for the social venue attendees can be specified as
        male_age_probabilities = {"18-65" : 0.3}
        any non-specified ages in the range (0,99) will have 0 probabilty
        Parameters
        ----------
        social_venues
            A SocialVenues object
        male_age_probabilities
            a dictionary containg age as keys and the probabilty per day (think of it as
            the Poisson parameter lambda) of a male person of that age going to the social
            venue as value. This probability value is per day. So the
            chance of going to the social venue in a time delta_t is
            1 - exp(- probabilty * delta_t)
        female_age_probabilities
            a dictionary containg age as keys and the probabilty of a female person of that age
            going to the social venue as value
        weekend_boost
            boosting factor for the weekend probability
        """
        self.social_venues = social_venues
        self.male_probabilities = parse_age_probabilities(male_age_probabilities)
        self.female_probabilities = parse_age_probabilities(female_age_probabilities)
        self.weekend_boost = weekend_boost
        self.neighbours_to_consider = neighbours_to_consider
        self.maximum_distance = maximum_distance
        self.drags_household_probability = drags_household_probability
        self.spec = re.findall("[A-Z][^A-Z]*", self.__class__.__name__)[:-1]
        self.spec = "_".join(self.spec).lower()

    def get_poisson_parameter(self, sex, age, is_weekend: bool = False):
        """
        Poisson parameter (lambda) of a person going to one social venue according to their
        age and sex and the distribution of visitors in the venue.

        Parameters
        ----------
        person
            an instance of Person
        delta_t
            interval of time in units of days
        is_weekend
            whether it is a weekend or not
        """
        if not self.social_venues:
            return 0
        if sex == "m":
            probability = self.male_probabilities[age]
        else:
            probability = self.female_probabilities[age]
        if is_weekend:
            probability = probability * self.weekend_boost
        return probability

    def probability_to_go_to_social_venue(
        self, person, delta_time, is_weekend: bool = False
    ):
        """
        Probabilty of a person going to one social venue according to their
        age and sex and the distribution of visitors in the venue.

        Parameters
        ----------
        person
            an instance of Person
        delta_t
            interval of time in units of days
        is_weekend
            whether it is a weekend or not
        """
        poisson_parameter = self.get_poisson_parameter(
            person.sex, person.age, is_weekend
        )
        return 1 - np.exp(-poisson_parameter * delta_time)

    def get_possible_venues_for_household(self, household: Household):
        house_location = household.area.coordinates
        potential_venues = self.social_venues.get_venues_in_radius(
            house_location, self.maximum_distance
        )
        if potential_venues is None:
            venue = self.social_venues.get_closest_venues(house_location, k=1)[0]
            return (venue,)

        potential_venues = np.random.choice(
            potential_venues[: min(len(potential_venues), self.neighbours_to_consider)],
            size=self.neighbours_to_consider,
        )
        return tuple(potential_venues,)

    def get_social_venue_for_person(self, person):
        """
        Adds a person to one of the social venues in the distributor. To decide, we select randomly
        from a certain number of neighbours, or the closest venue if the distance is greater than
        the maximum_distance.

        Parameters
        ----------
        person
            
        """
        person_location = person.area.coordinates
        potential_venues = self.social_venues.get_venues_in_radius(
            person_location, self.maximum_distance
        )
        if potential_venues is None:
            venue = self.social_venues.get_closest_venues(person_location, k=1)[0]
            return venue
        else:
            venue_candidates = np.random.choice(
                potential_venues[
                    : min(len(potential_venues), self.neighbours_to_consider)
                ],
                size=self.neighbours_to_consider,
            )
            for venue in venue_candidates:
                if venue.size < venue.max_size:
                    return venue
            return venue_candidates[0]

    def person_drags_household(self):
        """
        Check whether person drags household or not.
        """
        if self.drags_household_probability == 0.0:
            return False
        else:
            return np.random.rand() < self.drags_household_probability
