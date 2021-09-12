import numpy as np
from random import choice, random, sample, randint
from numba import jit, typed
from typing import Dict
from itertools import chain
import yaml
import re

from june.groups.leisure import SocialVenues, SocialVenue, SocialVenueError
from june.groups import Household, ExternalSubgroup
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
        leisure_subgroup_type=0,
    ):
        """
        A sex/age profile for the social venue attendees can be specified as
        male_age_probabilities = {"18-65" : 0.3}
        any non-specified ages in the range (0,99) will have 0 probabilty
        Parameters
        ----------
        social_venues
            A SocialVenues object
        times_per_week:
            How many times per day type, age, and sex, a person does this activity.
            Example:
            times_per_week = {"weekday" : {"male" : {"0-50":0.5, "50-100" : 0.2},
                                            "female" : {"0-100" : 0.5}},
                              "weekend" : {"male" : {"0-100" : 1.0},
                                            "female" : {"0-100" : 1.0}}}
        hours_per_day:
            How many leisure hours per day a person has. This is the time window in which
            a person can do leisure.
            Example:
            hours_per_day = {"weekday" : {"male" : {"0-65": 3, "65-100" : 11},
                                          "female" : {"0-65" : 3, "65-100" : 11}},
                              "weekend" : {"male" : {"0-100" : 12},
                                            "female" : {"0-100" : 12}}}
        drags_household_probabilitiy:
            Probability of doing a certain activity together with the housheold.
        maximum_distance:
            Maximum distance to travel until the social venue
        leisure_subgroup_type
            Subgroup of the venue that the person will be appended to
            (for instance, the visitors subgroup of the care home)
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
        self.leisure_subgroup_type = leisure_subgroup_type
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

    def get_poisson_parameter(
        self,
        sex,
        age,
        day_type,
        working_hours,
        region=None,
        policy_reduction=None,
    ):
        """
        Poisson parameter (lambda) of a person going to one social venue according to their
        age and sex and the distribution of visitors in the venue.

        Parameters
        ----------
        person
            an instance of Person
        delta_t
            interval of time in units of days
        weekday or weekend

            whether it is a weekend or not
        """
        if region is None:
            regional_compliance = 1
        else:
            if self.spec in region.closed_venues:
                return 0
            regional_compliance = region.regional_compliance
        original_poisson_parameter = self.poisson_parameters[day_type][sex][age]
        if policy_reduction is None:
            return original_poisson_parameter
        poisson_parameter = original_poisson_parameter * (
            1 + regional_compliance * (policy_reduction - 1)
        )
        return poisson_parameter

    def probability_to_go_to_social_venue(
        self, person, delta_time, day_type, working_hours
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
        day_type
            weekday or weekend
        """
        poisson_parameter = self.get_poisson_parameter(
            sex=person.sex,
            age=person.age,
            day_type=day_type,
            working_hours=working_hours,
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
            return (closest_venue[0],)
        indices_len = min(len(potential_venues), self.neighbours_to_consider)
        random_idx_choice = sample(range(len(potential_venues)), indices_len)
        return tuple([potential_venues[idx] for idx in random_idx_choice])

    def get_leisure_group(self, person):
        candidates = person.area.social_venues[self.spec]
        n_candidates = len(candidates)
        if n_candidates == 0:
            return
        elif n_candidates == 1:
            group = candidates[0]
        else:
            group = candidates[randint(0, n_candidates - 1)]
        return group

    def get_leisure_subgroup(self, person, to_send_abroad=None):
        group = self.get_leisure_group(person)
        # this may not necessary be the same subgroup, allow for customization here.
        if group is None:
            return
        subgroup = group.get_leisure_subgroup(
            person=person,
            subgroup_type=self.leisure_subgroup_type,
            to_send_abroad=to_send_abroad,
        )
        return subgroup

    def person_drags_household(self):
        """
        Check whether person drags household or not.
        """
        return random() < self.drags_household_probability

    def send_household_with_person_if_necessary(self, person, to_send_abroad=None):
        """
        When we know that the person does an activity in the social venue X,
        then we ask X whether the person needs to drag the household with
        him or her.
        """
        if (
            person.residence.group.spec == "care_home"
            or person.residence.group.type in ["communal", "other", "student"]
        ):
            return
        subgroup = person.leisure
        if self.person_drags_household():
            for mate in person.residence.group.residents:
                if mate != person:
                    if mate.busy:
                        if (
                            mate.leisure is not None
                        ):  # this perosn has already been assigned somewhere
                            if not mate.leisure.external:
                                if mate not in mate.leisure.people:
                                    # person active somewhere else, let's not disturb them
                                    continue
                                mate.leisure.remove(mate)
                            else:
                                ret = to_send_abroad.delete_person(mate, mate.leisure)
                                if ret:
                                    # person active somewhere else, let's not disturb them
                                    continue
                            if not subgroup.external:
                                subgroup.append(mate)
                            else:
                                to_send_abroad.add_person(mate, subgroup)
                    mate.subgroups.leisure = (
                        subgroup  # person will be added later in the simulator.
                    )
