from covid.groups.people import demography as d
import pytest


@pytest.fixture(
    name="demography"
)
def make_demography():
    return d.Demography.from_super_area(
        "NorthEast"
    )


def test_create_demography(demography):
    assert demography.super_area == "NorthEast"
    assert demography.residents_map["E00062207"] == 242


def test_population_size(demography):
    population = demography.population_for_area(
        "E00062207"
    )
    assert len(population) == 242
