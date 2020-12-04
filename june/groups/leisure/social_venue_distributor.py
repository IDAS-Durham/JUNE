import numpy as np
from random import choice, random, sample, randint
from numba import jit, typed
from typing import Dict
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
        times_per_week: Dict[Dict, float],
        hours_per_day: Dict[Dict, float] = None,
        drags_household_probability=0.0,
        neighbours_to_consider=5,
        maximum_distance=5,
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
        if hours_per_day is None:
            hours_per_day = {
                "weekday": {
                    "male": {"0-65": 3, "65-100": 11},
                    "female": {"0-65": 3, "65-100": 11},
                },
                "weekend": {"male": {"0-100": 12}, "female": {"0-100": 12}},
            }
        self.social_venues = social_venues
        self.poisson_parameters = self._parse_poisson_parameters(
            times_per_week=times_per_week, hours_per_day=hours_per_day
        )
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

    def _compute_poisson_parameter_from_times_per_week(
        self, times_per_week, hours_per_day, day_type
    ):
        if times_per_week == 0:
            return 0
        if day_type == "weekend":
            days = 2
        else:
            days = 5
        return times_per_week / days * 24 / hours_per_day

    def _parse_poisson_parameters(self, times_per_week, hours_per_day):
        ret = {}
        _sex_t = {"male": "m", "female": "f"}
        for day_type in ["weekday", "weekend"]:
            ret[day_type] = {}
            for sex in ["male", "female"]:
                parsed_times_per_week = parse_age_probabilities(
                    times_per_week[day_type][sex]
                )
                parsed_hours_per_day = parse_age_probabilities(
                    hours_per_day[day_type][sex]
                )
                ret[day_type][_sex_t[sex]] = [
                    self._compute_poisson_parameter_from_times_per_week(
                        times_per_week=parsed_times_per_week[i],
                        hours_per_day=parsed_hours_per_day[i],
                        day_type=day_type,
                    )
                    for i in range(len(parsed_times_per_week))
                ]
        return ret

    def get_poisson_parameter(self, sex, age, day_type):
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
        poisson_parameter = self.poisson_parameters[day_type][sex][age]
        return poisson_parameter

    def get_weekend_boost(self, is_weekend):
        if is_weekend:
            return self.weekend_boost
        else:
            return 1.0

    def probability_to_go_to_social_venue(self, person, delta_time, day_type):
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
        poisson_parameter = self.get_poisson_parameter(person.sex, person.age, day_type)
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
            return (closest_venue[0],)
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
