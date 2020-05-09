import pytest

from june.demography import demographics as d


@pytest.fixture(
    name="demography"
)
def make_demography(super_area):
    return d.Demography.for_super_area(
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


@pytest.fixture(
    name="population"
)
def make_population(demography, area):
    return demography.population_for_area(
        area
    )


def test_create_demography(demography, super_area, area):
    assert demography.super_area == super_area
    assert demography.residents_map[area] == 242
    assert len(demography.sex_generators) == 8802


def test_get_population(population, area):
    assert population.area == area
    assert len(population) == 242


def test_sex(population):
    sexes = [
        person.sex
        for person
        in population
    ]
    assert "m" in sexes
    assert "f" in sexes


def test_age(population):
    for person in population:
        assert 0 <= person.age <= 100


def test_weighted_generator():
    weighted_generator = d.WeightedGenerator(
        (0.0, 10),
        (1.0, 20)
    )
    assert weighted_generator() == 20

    weighted_generator = d.WeightedGenerator(
        (1.0, 10),
        (0.0, 20)
    )
    assert weighted_generator() == 10


def test_age_generator():
    age_generator = d.AgeGenerator.from_range_string(
        "0-10"
    )
    assert age_generator.lower == 0
    assert age_generator.upper == 10

    age_generator = d.AgeGenerator.from_range_string(
        "90-XXX"
    )
    assert age_generator.lower == 90
    assert age_generator.upper == 100

    assert d.AgeGenerator(
        10, 10
    )() == 10


def test_health_index(population):
    health_indices = [
        person.health_index
        for person
        in population
    ]
    assert isinstance(health_indices[0][0], float)
