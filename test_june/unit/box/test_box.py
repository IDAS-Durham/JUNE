from june.box import Box, Boxes
from june.geography import Geography
from june.demography import Demography, Population
import pytest


@pytest.fixture(name="population_box")
def make_population():
    geography = Geography.from_file({"area": ["E00062194"]})
    demography = Demography.for_geography(geography)
    population = Population() 
    for area in geography.areas:
        population.extend(demography.populate(area.name))
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
    assert len(box.people) == len(population_box)
    person.dead == True
    assert len(box.dead) == 0
    assert len(box.people) == len(population_box)

