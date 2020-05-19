import numpy as np
from pytest import fixture
from scipy.stats import poisson

from june.distributors import SocialVenueDistributor
from june.groups import SocialVenue, SocialVenues
from june.demography import Person


@fixture(name="social_venues")
def make_social_venues():
    ll = []
    for _ in range(10):
        ll.append(SocialVenue())
    return SocialVenues(ll)


@fixture(name="social_venue_distributor")
def make_distributor(social_venues):
    male_dict = {"18-65": 0.5, "66-70": 0.2}
    female_dict = {"18-65": 0.1, "66-70": 0.8}
    weekend_boost = 2
    return SocialVenueDistributor(social_venues, male_dict, female_dict, weekend_boost)


def test__decide_person_goes_to_social_venue(social_venue_distributor):
    person = Person(age=40, sex="m")
    goes_to_venue = 0
    goes_to_venue_weekend = 0
    for _ in range(100):
        goes_to_venue += int(
            social_venue_distributor.goes_to_social_venue(
                person, delta_time=1, is_weekend=False
            )
        )
        goes_to_venue_weekend += int(
            social_venue_distributor.goes_to_social_venue(
                person, delta_time=1, is_weekend=True
            )
        )
    assert np.isclose(goes_to_venue, poisson.rvs(0.5 * 100), atol=0, rtol=0.1)
    assert np.isclose(goes_to_venue_weekend, 100, atol=0, rtol=0.1)
