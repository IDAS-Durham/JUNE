import numpy as np
from random import choice, random, sample, randint
from numba import jit
from numba import typed
from itertools import chain
import yaml
import re

from june.groups.leisure import SocialVenues, SocialVenue, SocialVenueError
from june.groups import Household
from june.utils.parse_probabilities import parse_age_probabilities
from june.geography import Area


@jit(nopython=True)
def random_choice_numba(arr, prob):
    """
    Fast implementation of np.random.choice
    """
    return arr[np.searchsorted(np.cumsum(prob), random(), side="right")]



class SocialVenueDistributor:
    """
    Tool to associate social venues to people.
    """

    def __init__(
        self,
        social_venues: SocialVenues,
        poisson_parameters: dict = None,
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
        poisson_parameters
            A dictionary with sex as keys, and as values another dictionary specifying the 
            poisson parameters by age for the activity. Example:
            poisson_parameters = {"m" : {"0-50":0.5, "50-100" : 0.2, "f" : {"0-100" : 0.5}}
            Note that the upper limit of the age bracket is not inclusive.
            The probability of going into a social venue will then be determined by
            1 - exp(-poisson_parameter(age,sex) * delta_t * weekend_boost)
        weekend_boost
            boosting factor for the weekend probability
        """
        self.social_venues = social_venues
        self.poisson_parameters = self._parse_poisson_parameters(poisson_parameters)
        self.weekend_boost = weekend_boost
        self.neighbours_to_consider = neighbours_to_consider
        self.maximum_distance = maximum_distance
        self.drags_household_probability = drags_household_probability
        self.spec = re.findall("[A-Z][^A-Z]*", self.__class__.__name__)[:-1]
        self.spec = "_".join(self.spec).lower()

    @classmethod
    def from_config(cls, social_venues: SocialVenues, config_filename: str = None):
        if config_filename is None:
            config_filename = cls.default_config_filename
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(social_venues, **config)

    def _parse_poisson_parameters(self, poisson_parameters):
        ret = {}
        ret["m"] = parse_age_probabilities(poisson_parameters["male"])
        ret["f"] = parse_age_probabilities(poisson_parameters["female"])
        return ret


    def get_poisson_parameter(self, sex, age, is_weekend: bool = False, policy_poisson_parameter=None, region=None):
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
        if region is None:
            regional_compliance = 1
        else:
            if self.spec in region.closed_venues:
                return 0
            regional_compliance = region.regional_compliance
        original_poisson_parameter = self.poisson_parameters[sex][age]
        original_poisson_parameter = original_poisson_parameter * self.get_weekend_boost(is_weekend)
        if policy_poisson_parameter is None:
            return original_poisson_parameter

        poisson_parameter = (
            original_poisson_parameter
            + regional_compliance
            * (policy_poisson_parameter - original_poisson_parameter)
        )
        return poisson_parameter

    def get_weekend_boost(self, is_weekend):
        if is_weekend:
            return self.weekend_boost
        else:
            return 1.0

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

    def get_possible_venues_for_area(self, area: Area):
        """
        Given an area, searches for the social venues inside
        ``self.maximum_distance``. It then returns ``self.neighbours_to_consider``
        of them randomly. If there are no social venues inside the maximum distance,
        it returns the closest one.
        """
        area_location = area.coordinates
        potential_venues = self.social_venues.get_venues_in_radius(
            area_location, self.maximum_distance
        )
        if potential_venues is None:
            closest_venue = self.social_venues.get_closest_venues(area_location, k=1)
            if closest_venue is None:
                return
            return (closest_venue[0], )
        indices_len = min(len(potential_venues), self.neighbours_to_consider)
        random_idx_choice = sample(range(len(potential_venues)), indices_len)
        return tuple([potential_venues[idx] for idx in random_idx_choice])

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
            return self.social_venues.get_closest_venues(person_location, k=1)[0]
        else:
            return choice(
                potential_venues[
                    : min(len(potential_venues), self.neighbours_to_consider)
                ]
            )

    def person_drags_household(self):
        """
        Check whether person drags household or not.
        """
        return random() < self.drags_household_probability

    def get_leisure_subgroup_type(self, person):
        return 0


