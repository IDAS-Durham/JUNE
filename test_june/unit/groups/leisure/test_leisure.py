import numpy as np
from pytest import fixture
from june.groups import Household
from june.demography.geography import Area, SuperArea
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
from june.demography.geography import Geography
from june.demography import Person, Demography
from june import World


@fixture(name="geography")
def make_geography():
    geography = Geography.from_file({"super_area": ["E02000140"]})
    return geography


@fixture(name="leisure")
def make_leisure():
    pubs = Pubs([Pub()], make_tree=False)
    pub_distributor = PubDistributor(
        pubs, male_age_probabilities={"18-50": 0.5}, drags_household_probability=0.0
    )
    cinemas = Cinemas([Cinema()], make_tree=False)
    cinema_distributor = CinemaDistributor(
        cinemas, male_age_probabilities={"10-40": 0.2}, drags_household_probability=1.0,
    )
    leisure = Leisure(
        leisure_distributors={"pubs": pub_distributor, "cinemas": cinema_distributor}
    )
    return leisure


def test__probability_of_leisure(leisure):
    person = Person.from_attributes(sex="m", age=26)
    estimated_time_for_activity = 1 / (0.5 + 0.2)
    delta_time = 0.01
    times = []
    times_goes_pub = 0
    times_goes_cinema = 0
    for _ in range(0, 300):
        counter = 0
        while True:
            counter += delta_time
            activity_distributor = leisure.get_leisure_distributor_for_person(
                person, delta_time
            )
            if activity_distributor is None:
                continue
            if activity_distributor.spec == "pub":
                times_goes_pub += 1
            elif activity_distributor.spec == "cinema":
                times_goes_cinema += 1
            else:
                raise ValueError
            times.append(counter)
            break
    assert np.isclose(np.mean(times), estimated_time_for_activity, atol=0.1, rtol=0)
    assert np.isclose(times_goes_pub / times_goes_cinema, 0.5 / 0.2, atol=0, rtol=0.25)


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
    social_venue = leisure.leisure_distributors["cinemas"].social_venues[0]
    social_venue.add(person1)
    leisure.send_household_with_person_if_necessary(
        person=person1,
        social_venue=social_venue,
        leisure_distributor=leisure.leisure_distributors["cinemas"],
    )
    for person in [person1, person2, person3]:
        assert person.subgroups.leisure == social_venue.subgroups[0]


def test__generate_leisure_from_world():
    geography = Geography.from_file({"super_area": ["E02000140"]})
    world = generate_world_from_geography(
        geography, include_households=False, include_commute=False
    )
    world.pubs = Pubs.for_geography(geography)
    world.cinemas = Cinemas.for_geography(geography)
    world.groceries = Groceries.for_super_areas(
        geography.super_areas, venues_per_capita=1 / 500
    )
    person = Person(sex="m", age=27)
    household = Household()
    household.add(person)
    person.area = geography.areas[0]
    assert np.isclose(
        len(world.groceries), len(world.people) * 1 / 500, atol=0, rtol=0.1
    )
    leisure = generate_leisure_for_world(
        list_of_leisure_groups=["pubs", "cinemas", "groceries"], world=world
    )
    for _ in range(0, 100):
        leisure.get_subgroup_for_person_and_housemates(person, 0.1, False)
