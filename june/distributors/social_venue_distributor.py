import numpy as np
from typing import List
from numba import jit
from itertools import chain

from june.groups import SocialVenues, SocialVenue, SocialVenueError

#@jit(nopython=True)
def _throw_poisson_dice(probability, delta_time):
    return np.random.rand() < (1 - np.exp(-probability * delta_time))

class SocialVenueDistributor:
    """
    Tool to associate social venues to people.
    """

    def __init__(
        self,
        social_venues: SocialVenues,
        male_age_probabilities: dict,
        female_age_probabilities: dict,
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
            a dictionary containg age as keys and the probabilty of a male person of that age
            going to the social venue as value. This probability value is per day. So the
            chance of going to the social venue in a time delta_t is
            1 - exp(- probabilty * delta_t)
        female_age_probabilities
            a dictionary containg age as keys and the probabilty of a female person of that age
            going to the social venue as value
        weekend_boost
            boosting factor for the weekend probability
        """
        self.social_venues = social_venues
        self.male_age_probabilities = male_age_probabilities
        self.female_age_probabilities = female_age_probabilities
        self.weekend_boost = weekend_boost
        self.male_bins, self.male_probabilities = self._parse_age_probabilites(
            male_age_probabilities
        )
        self.female_bins, self.female_probabilities = self._parse_age_probabilites(
            female_age_probabilities
        )

    def _parse_age_probabilites(self, age_dict):
        bins = []
        for age_range in age_dict:
            age_range_split = age_range.split("-")
            if len(age_range_split) == 1:
                raise SocialVenueError("Please give age ranges as intervals")
            else:
                bins.append(int(age_range_split[0]))
                bins.append(int(age_range_split[1]))
            probabilities.append(age_dict[age_range])
        sorting_idx = np.argsort(bins[::2])
        bins = list(chain(*[[bins[2*idx], bins[2*idx+1]] for idx in sorting_idx]))
        probabilities = np.array(probabilities)[sorting_idx]
        return bins, probabilities


    def goes_to_social_venue(self, person, delta_time, is_weekend: bool = False):
        """
        Decides whether the person goes to the social venue according to their
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
        age = person.age
        sex = person.sex
        if sex == "m":
            if age < self.male_bins[0] or age > self.male_bins[-1]:
                return 0
            else:
                idx = np.searchsorted(self.male_bins, age)
                probability = self.male_probabilities[idx]
                print(probability)
        else:
            if age < self.female_bins[0] or age > self.female_bins[-1]:
                return 0
            else:
                idx = np.searchsorted(self.female_bins, age)
                probability = self.female_probabilities[idx]
        if is_weekend:
            probability = probability * self.weekend_boost

        return _throw_poisson_dice(probability, delta_time)

    def add_person_to_social_venue(self, person, neighbours_to_consider = 5, maximum_distance=5):
        """
        Adds a person to one of the social venues in the distributor. To decide, we select randomly
        from a certain number of neighbours, or the closest venue if the distance is greater than
        the maximum_distance.

        Parameters
        ----------
        person
            
        """
        person_location = person.area.coordinates

