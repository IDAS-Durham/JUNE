import numpy as np
import random
from pytest import fixture
from scipy.stats import poisson

from june.groups.leisure import SocialVenueDistributor
from june.groups.leisure import SocialVenue, SocialVenues
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


@fixture(name="social_venue_distributor", scope="module")
def make_distributor(social_venues):
    male_dict = {"18-65": 0.5, "66-70": 0.2}
    female_dict = {"18-65": 0.1, "66-70": 0.8}
    weekend_boost = 2
    return SocialVenueDistributor(
        social_venues,
        male_dict,
        female_dict,
        weekend_boost=weekend_boost,
        maximum_distance=30,
    )

def test__age_dict_parsing(social_venue_distributor):
    age_dict = {"40-60" : 0.4, "10-20" : 0.2}
    bins, probs = social_venue_distributor._parse_age_probabilites(age_dict)
    assert bins == [10, 20, 40, 60]
    assert probs == [0.0, 0.2, 0.0,  0.4, 0.0]

def get_days_until_pub(person, delta_time, is_weekend, distrib):
    days = []
    for _ in range(600):
        counter = 0
        probability = distrib.probability_to_go_to_social_venue(
            person, delta_time=delta_time, is_weekend=is_weekend
        )
        while True:
            counter += delta_time
            if np.random.rand() < probability:
                days.append(counter)
                break
    return np.mean(days)


def test__decide_person_goes_to_social_venue(social_venue_distributor):
    dt = 0.01

    person = Person(age=40, sex="m")
    estimated_day_to_go_to_the_pub = 1 / 0.5
    estimated_day_to_go_to_the_pub_weekend = 1 / ( 2 * 0.5)
    rest = get_days_until_pub(person, dt, False, social_venue_distributor)
    assert np.isclose(rest, estimated_day_to_go_to_the_pub, atol=0, rtol=0.1)
    rest = get_days_until_pub(person, dt, True, social_venue_distributor)
    assert np.isclose(rest, estimated_day_to_go_to_the_pub_weekend, atol=0, rtol=0.1)


    person = Person(age=68, sex="m")
    estimated_day_to_go_to_the_pub = 1 / 0.2
    estimated_day_to_go_to_the_pub_weekend = 1 / ( 2 * 0.2)
    rest = get_days_until_pub(person, dt, False, social_venue_distributor)
    assert np.isclose(rest, estimated_day_to_go_to_the_pub, atol=0, rtol=0.1)
    rest = get_days_until_pub(person, dt, True, social_venue_distributor)
    assert np.isclose(rest, estimated_day_to_go_to_the_pub_weekend, atol=0, rtol=0.1)

    person = Person(age=20, sex="f")
    estimated_day_to_go_to_the_pub = 1 / 0.1
    estimated_day_to_go_to_the_pub_weekend = 1 / ( 2 * 0.1)
    rest = get_days_until_pub(person, dt, False, social_venue_distributor)
    assert np.isclose(rest, estimated_day_to_go_to_the_pub, atol=0, rtol=0.1)
    rest = get_days_until_pub(person, dt, True, social_venue_distributor)
    assert np.isclose(rest, estimated_day_to_go_to_the_pub_weekend, atol=0, rtol=0.1)

class MockArea:
    def __init__(self):
        self.coordinates = np.array([10, 11])


def test__add_person_to_social_venues(social_venues, social_venue_distributor):
    social_venues.make_tree()
    person = Person(age=20, sex="m")
    person.area = MockArea()
    social_venue = social_venue_distributor.get_social_venue_for_person(person)
    social_venue.add(person)
    social_venue = social_venues[-1]
    assert person.subgroups[person.ActivityType.dynamic] == social_venue[0]
    # not added to group
    assert len(social_venue.people) == 0
