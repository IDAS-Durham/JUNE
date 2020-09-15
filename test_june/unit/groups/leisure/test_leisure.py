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


@fixture(name="geography")
def make_geography():
    geography = Geography.from_file({"super_area": ["E02000140"]})
    return geography


@fixture(name="leisure")
def make_leisure():
    pubs = Pubs([Pub()], make_tree=False)
    pub_distributor = PubDistributor(
        pubs,
        male_age_probabilities={"18-50": 0.5},
        female_age_probabilities={"10-40": 0.2},
        drags_household_probability=0.0,
    )
    pubs[0].coordinates = [1, 2]
    cinemas = Cinemas([Cinema()], make_tree=False)
    cinemas[0].coordinates = [1, 2]
    cinema_distributor = CinemaDistributor(
        cinemas,
        male_age_probabilities={"10-40": 0.2},
        female_age_probabilities={"10-40": 0.2},
        drags_household_probability=1.0,
    )
    leisure = Leisure(
        leisure_distributors={"pubs": pub_distributor, "cinemas": cinema_distributor}
    )
    leisure.generate_leisure_probabilities_for_timestep(0.01, False, False)
    return leisure


def test__probability_of_leisure(leisure):
    person = Person.from_attributes(sex="m", age=26)
    household = Household(type="student")
    household.add(person)
    person.residence.group.social_venues = {
        "cinemas": [leisure.leisure_distributors["cinemas"].social_venues[0]],
        "pubs": [leisure.leisure_distributors["pubs"].social_venues[0]],
    }

    estimated_time_for_activity = 1 / (0.5 + 0.2)
    times = []
    times_goes_pub = 0
    times_goes_cinema = 0
    for _ in range(0, 300):
        counter = 0
        while True:
            counter += 0.01
            subgroup = leisure.get_subgroup_for_person_and_housemates(person)
            if subgroup is None:
                continue
            if subgroup.group.spec == "pub":
                times_goes_pub += 1
            elif subgroup.group.spec == "cinema":
                times_goes_cinema += 1
            else:
                raise ValueError
            times.append(counter)
            break
    assert np.isclose(np.mean(times), estimated_time_for_activity, atol=0.2, rtol=0)
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
        person1, person1.leisure, 1.0,
    )
    for person in [person1, person2, person3]:
        assert person.subgroups.leisure == social_venue.subgroups[0]


def test__generate_leisure_from_world():
    geography = Geography.from_file({"super_area": ["E02002135"]})
    world = generate_world_from_geography(
        geography, include_households=True, include_commute=False
    )
    world.pubs = Pubs.for_geography(geography)
    world.cinemas = Cinemas.for_geography(geography)
    world.groceries = Groceries.for_geography(geography)
    person = Person.from_attributes(sex="m", age=27)
    household = Household()
    household.area = world.areas[0]
    household.add(person)
    person.area = geography.areas[0]
    leisure = generate_leisure_for_world(
        list_of_leisure_groups=["pubs", "cinemas", "groceries"], world=world
    )
    leisure.distribute_social_venues_to_households([household], super_areas=world.super_areas)
    leisure.generate_leisure_probabilities_for_timestep(0.1, False, False)
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
    assert 0 < n_pubs < 100
    assert 0 < n_cinemas < 100
    assert 0 < n_groceries < 107
