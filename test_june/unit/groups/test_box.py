from june.box import Box, Boxes
from june.geography import Geography
from june.demography import Demography
import pytest


@pytest.fixture(name="population_box")
def make_population():
    geography = Geography.from_file({"oa": ["E00062194"]})
    demography = Demography.for_geography(geography)
    population = demography.populate(geography.areas)
    return population


@pytest.fixture(name="box")
def make_box(population_box):
    box = Box()
    box.set_population(population_box)
    return box


def test__population_box(box, population_box):
    assert len(box.people) == len(population_box)


def test__box_infected_properties(box, population_box):
    person = list(box.people)[0]
    person.health_information.infected = True
    assert len(box.infected) == 1
    assert len(box.people) == len(population_box)
    person.health_information.infected = False
    person.health_information.recovered = True
    assert len(box.recovered) == 1
    assert len(box.infected) == 0
    person.health_information.dead == True
    assert len(box.dead) == 0
    assert len(box.people) == len(population_box)