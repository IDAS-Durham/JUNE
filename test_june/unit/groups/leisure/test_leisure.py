import numpy as np
from pytest import fixture
from june.groups import Household
from june.geography import Area, SuperArea
from june.world import generate_world_from_geography

from june.groups.leisure import (
    Leisure,
    generate_leisure_for_world,
    Pub,
    Pubs,
    Cinemas,
    Cinema,
    Groceries,
    PubDistributor,
    CinemaDistributor,
)
from june.geography import Geography
from june.demography import Person, Demography
from june import World


class MockArea:
    def __init__(self):
        pass


@fixture(name="leisure")
def make_leisure():
    pubs = Pubs([Pub()], make_tree=False)
    pub_distributor = PubDistributor(
        pubs,
        times_per_week={
            "weekday": {"male": {"18-50": 0.5}, "female": {"10-40": 0.3}},
            "weekend": {"male": {"18-50": 0.7}, "female": {"18-50": 0.4}},
        },
    )
    pubs[0].coordinates = [1, 2]
    cinemas = Cinemas([Cinema()], make_tree=False)
    cinemas[0].coordinates = [1, 2]
    cinema_distributor = CinemaDistributor(
        cinemas,
        times_per_week={
            "weekday": {"male": {"10-40": 0.1}, "female": {"10-40": 0.2}},
            "weekend": {"male": {"18-50": 0.4}, "female": {"18-50": 0.5}},
        },
        drags_household_probability=1.0,
    )
    leisure = Leisure(
        leisure_distributors={"pub": pub_distributor, "cinema": cinema_distributor}
    )
    return leisure


def _get_times_pub_cinema(leisure, person, day_type):
    if day_type == "weekend":
        delta_time = 0.125  # in reality is 0.5 but make it smaller for stats
        n_days = 8  # in reality is 2
    else:
        delta_time = 1 / 8
        n_days = 5
    leisure.generate_leisure_probabilities_for_timestep(
        delta_time, working_hours=False, day_type=day_type
    )
    times_goes_pub = []
    times_goes_cinema = []
    for _ in range(0, 5000):
        goes_pub = 0
        goes_cinema = 0
        for _ in range(n_days):  # one week
            subgroup = leisure.get_subgroup_for_person_and_housemates(person)
            if subgroup is None:
                continue
            if subgroup.group.spec == "pub":
                goes_pub += 1
            elif subgroup.group.spec == "cinema":
                goes_cinema += 1
            else:
                raise ValueError
        times_goes_pub.append(goes_pub)
        times_goes_cinema.append(goes_cinema)
    times_pub_a_week = np.mean(times_goes_pub)
    times_cinema_a_week = np.mean(times_goes_cinema)
    return times_pub_a_week, times_cinema_a_week


def test__probability_of_leisure(leisure):
    household = Household(type="student")
    male = Person.from_attributes(sex="m", age=26)
    male.area = MockArea()
    household.add(male)
    female = Person.from_attributes(sex="f", age=26)
    female.area = MockArea()
    household.add(female)
    male.area.social_venues = {
        "cinema": [leisure.leisure_distributors["cinema"].social_venues[0]],
        "pub": [leisure.leisure_distributors["pub"].social_venues[0]],
    }
    female.area.social_venues = {
        "cinema": [leisure.leisure_distributors["cinema"].social_venues[0]],
        "pub": [leisure.leisure_distributors["pub"].social_venues[0]],
    }
    # weekday male
    times_pub_a_week, times_cinema_a_week = _get_times_pub_cinema(
        person=male, leisure=leisure, day_type="weekday"
    )
    assert np.isclose(times_pub_a_week, 0.5, rtol=0.1)
    assert np.isclose(times_cinema_a_week, 0.1, rtol=0.1)
    # weekday female
    times_pub_a_week, times_cinema_a_week = _get_times_pub_cinema(
        person=female, leisure=leisure, day_type="weekday"
    )
    assert np.isclose(times_pub_a_week, 0.3, rtol=0.1)
    assert np.isclose(times_cinema_a_week, 0.2, rtol=0.1)
    # weekend male
    times_pub_a_week, times_cinema_a_week = _get_times_pub_cinema(
        person=male, leisure=leisure, day_type="weekend"
    )
    assert np.isclose(times_pub_a_week, 0.7, rtol=0.1)
    assert np.isclose(times_cinema_a_week, 0.4, rtol=0.1)
    # weekend female
    times_pub_a_week, times_cinema_a_week = _get_times_pub_cinema(
        person=female, leisure=leisure, day_type="weekend"
    )
    assert np.isclose(times_pub_a_week, 0.4, rtol=0.1)
    assert np.isclose(times_cinema_a_week, 0.5, rtol=0.1)


def test__person_drags_household(leisure):
    person1 = Person.from_attributes(sex="m", age=26)
    person2 = Person.from_attributes(sex="f", age=26)
    person3 = Person.from_attributes(sex="m", age=27)
    household = Household()
    household.add(person1)
    household.add(person2)
    household.add(person3)
    person2.busy = False
    person3.busy = False
    social_venue = leisure.leisure_distributors["cinema"].social_venues[0]
    social_venue.add(person1)
    leisure.leisure_distributors["cinema"].send_household_with_person_if_necessary(
        person1, None
    )
    for person in [person1, person2, person3]:
        assert person.subgroups.leisure == social_venue.subgroups[0]


def test__generate_leisure_from_world(dummy_world):
    world = dummy_world
    person = Person.from_attributes(sex="m", age=27)
    household = Household()
    household.area = world.areas[0]
    household.add(person)
    person.area = world.areas[0]
    leisure = generate_leisure_for_world(
        list_of_leisure_groups=["pubs", "cinemas", "groceries"], world=world
    )
    leisure.generate_leisure_probabilities_for_timestep(0.1, False, day_type="weekday")
    n_pubs = 0
    n_cinemas = 0
    n_groceries = 0
    for _ in range(0, 1000):
        subgroup = leisure.get_subgroup_for_person_and_housemates(person)
        if subgroup is not None:
            if subgroup.group.spec == "pub":
                n_pubs += 1
            elif subgroup.group.spec == "cinema":
                n_cinemas += 1
            elif subgroup.group.spec == "grocery":
                n_groceries += 1
    assert 0 < n_pubs
    assert 0 < n_cinemas
    assert 0 < n_groceries
