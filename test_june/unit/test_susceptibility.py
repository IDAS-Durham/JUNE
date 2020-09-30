import pytest

from june.utils import parse_age_probabilities
from june.interaction import Interaction
from june.demography import Population, Person


@pytest.fixture(name="susceptibility_dict")
def make_susc():
    return {"0-13": 0.5, "13-100": 1.0}


class TestInteractionChangesSusceptibility:
    def test__susceptibility_parser(self, susceptibility_dict):
        susceptibilities_parsed = parse_age_probabilities(susceptibility_dict)
        for i in range(0, 100):
            if i < 13:
                assert susceptibilities_parsed[i] == 0.5
            else:
                assert susceptibilities_parsed[i] == 1.0

    def test__interaction_changes_susceptibility(self, susceptibility_dict):
        population = Population([])
        for i in range(105):
            population.add(Person.from_attributes(age=i))
        for person in population:
            assert person.susceptibility == 1.0
        interaction = Interaction(
            beta=None,
            alpha_physical=None,
            contact_matrices=None,
            susceptibilities_by_age=susceptibility_dict,
            population = population
        )
        for person in population:
            if person.age < 13:
                assert person.susceptibility == 0.5
            else:
                assert person.susceptibility == 1.0

