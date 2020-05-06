import pytest

from covid.groups.people import demography as d


@pytest.fixture(
    name="demography"
)
def make_demography(super_area):
    return d.Demography.from_super_area(
        super_area
    )


@pytest.fixture(
    name="super_area"
)
def make_super_area():
    return "NorthEast"


@pytest.fixture(
    name="area"
)
def make_area():
    return "E00062207"


def test_create_demography(demography, super_area, area):
    assert demography.super_area == super_area
    assert demography.residents_map[area] == 242


def test_get_population(demography, area):
    population = demography.population_for_area(
        area
    )
    assert population.area == area
    assert len(population) == 242
