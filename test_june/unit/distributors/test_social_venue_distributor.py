import numpy as np
import random
from pytest import fixture
from scipy.stats import poisson
from random import random

from june.groups.leisure import SocialVenueDistributor
from june.groups.leisure import SocialVenue, SocialVenues
from june.utils.parse_probabilities import parse_age_probabilities
from june.demography import Person


@fixture(name="social_venues", scope="module")
def make_social_venues():
    ll = []
    for _ in range(10):
        social_venue = SocialVenue()
        social_venue.coordinates = np.array([1, 2])
        ll.append(social_venue)
    ll[-1].coordinates = np.array([10, 10])
    social_venues = SocialVenues(ll)
    return social_venues


@fixture(name="sv_input", scope="module")
def make_input():
    times_per_week = {
        "weekday": {
            "male": {"18-65": 2, "65-100": 1},
            "female": {"18-65": 1, "65-100": 0.5},
        },
        "weekend": {"male": {"18-100": 3}, "female": {"18-100": 3}},
    }
    hours_per_day = {
        "weekday": {
            "male": {"18-65": 3, "65-100": 11},
            "female": {"18-65": 3, "65-100": 11},
        },
        "weekend": {"male": {"18-100": 12}, "female": {"18-100": 12}},
    }
    return times_per_week, hours_per_day


@fixture(name="social_venue_distributor", scope="module")
def make_distributor(social_venues, sv_input):
    times_per_week, hours_per_day = sv_input
    return SocialVenueDistributor(
        social_venues,
        times_per_week=times_per_week,
        hours_per_day=hours_per_day,
        maximum_distance=30,
    )


class TestInput:
    def test__age_dict_parsing(self):
        age_dict = {"40-60": 0.4, "10-20": 0.2}
        probabilities_per_age = parse_age_probabilities(age_dict)
        for idx, prob in enumerate(probabilities_per_age):
            if idx < 10:
                assert prob == 0.0
            elif idx < 20:
                assert prob == 0.2
            elif idx < 40:
                assert prob == 0.0
            elif idx < 60:
                assert prob == 0.4
            else:
                assert prob == 0.0

    def test__read_input_times_a_week(self, social_venue_distributor):
        poisson_parameters = social_venue_distributor.poisson_parameters
        for age in range(0, 18):
            assert poisson_parameters["weekday"]["m"][age] == 0
            assert poisson_parameters["weekday"]["f"][age] == 0
            assert poisson_parameters["weekend"]["m"][age] == 0
            assert poisson_parameters["weekend"]["f"][age] == 0
        for age in range(18, 65):
            assert np.isclose(
                poisson_parameters["weekday"]["m"][age], 2 * 1 / 5 * 24 / 3
            )
            assert np.isclose(
                poisson_parameters["weekday"]["f"][age], 1 * 1 / 5 * 24 / 3
            )
            assert np.isclose(
                poisson_parameters["weekend"]["m"][age], 3 * 1 / 2 * 24 / 12
            )
            assert np.isclose(
                poisson_parameters["weekend"]["f"][age], 3 * 1 / 2 * 24 / 12
            )
        for age in range(65, 100):
            assert np.isclose(
                poisson_parameters["weekday"]["m"][age], 1 * 1 / 5 * 24 / 11
            )
            assert np.isclose(
                poisson_parameters["weekday"]["f"][age],  0.5 * 1 / 5 * 24 / 11
            )
            assert np.isclose(
                poisson_parameters["weekend"]["m"][age],  3 * 1 / 2 * 24 / 12
            )
            assert np.isclose(
                poisson_parameters["weekend"]["f"][age],  3 * 1 / 2 * 24 / 12
            )


class TestProbabilities:
    def get_n_times_a_week(self, person, delta_time, day_type, distrib):
        if day_type == "weekday":
            max_time = 5
        else:
            max_time = 2
        times = []
        for _ in range(100):
            time = 0
            times_this_week = 0
            while time < max_time:
                time += 0.25
                probability = distrib.probability_to_go_to_social_venue(
                    person, delta_time=delta_time, day_type=day_type, working_hours=False
                )
                if random() < probability:
                    times_this_week += 1
            times.append(times_this_week)
        return np.mean(times) 

    def test__decide_person_goes_to_social_venue(
        self, social_venue_distributor, sv_input
    ):
        times_per_week, hours_per_day = sv_input

        # young weekday #
        dt = 3 / 4 /24  # in days
        person = Person(age=40, sex="m")
        times_per_week_weekday = times_per_week["weekday"]["male"]["18-65"]
        rest = self.get_n_times_a_week(
            person, dt, "weekday", social_venue_distributor
        )
        assert np.isclose(rest, times_per_week_weekday, atol=0, rtol=0.2)

        # young weekend #
        dt = 3/24
        times_per_week_weekend = times_per_week["weekend"]["male"]["18-100"]
        rest = self.get_n_times_a_week(
            person, dt, "weekend", social_venue_distributor
        )
        assert np.isclose(rest, times_per_week_weekend, atol=0, rtol=0.2)

        # retired weekday
        dt = 11 / 4 / 24
        person = Person(age=68, sex="f")
        times_per_week_weekday = times_per_week["weekday"]["female"]["65-100"]
        rest = self.get_n_times_a_week(
            person, dt, "weekday", social_venue_distributor
        )
        assert np.isclose(rest, times_per_week_weekday, atol=0, rtol=0.2)

        # retired weekend
        dt = 3 / 24
        times_per_week_weekend = times_per_week["weekend"]["female"]["18-100"]
        rest = self.get_n_times_a_week(
            person, dt, "weekend", social_venue_distributor
        )
        assert np.isclose(rest, times_per_week_weekend, atol=0, rtol=0.2)

    class MockArea:
        def __init__(self):
            self.coordinates = np.array([10, 11])
