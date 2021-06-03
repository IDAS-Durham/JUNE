import pytest

from june.utils import parse_age_probabilities
from june.epidemiology.infection import Covid19, B117, SusceptibilitySetter
from june.demography import Person, Population


@pytest.fixture(name="susceptibility_dict")
def make_susc():
    return {
        Covid19.infection_id(): {"0-13": 0.5, "13-100": 1.0},
        B117.infection_id(): {"20-40": 0.25},
    }


class TestSusceptibilitySetter:
    def test__susceptibility_parser(self, susceptibility_dict):
        susc_setter = SusceptibilitySetter(susceptibility_dict)
        susceptibilities_parsed = susc_setter.susceptibility_dict
        c19_id = Covid19.infection_id()
        b117_id = B117.infection_id()
        for i in range(0, 100):
            if i < 13:
                assert susceptibilities_parsed[c19_id][i] == 0.5
            else:
                assert susceptibilities_parsed[c19_id][i] == 1.0
            if i < 20:
                assert susceptibilities_parsed[b117_id][i] == 1.0
            elif i < 40:
                assert susceptibilities_parsed[b117_id][i] == 0.25
            else:
                assert susceptibilities_parsed[b117_id][i] == 1.0

    def test__susceptiblity_setter(self, susceptibility_dict):
        population = Population([])
        for i in range(105):
            population.add(Person.from_attributes(age=i))

        susceptibility_setter = SusceptibilitySetter(susceptibility_dict)
        susceptibility_setter.set_susceptibilities(population)
        c19_id = Covid19.infection_id()
        b117_id = B117.infection_id()

        for person in population:
            if person.age < 13:
                assert person.immunity.susceptibility_dict[c19_id] == 0.5
            else:
                assert person.immunity.susceptibility_dict[c19_id] == 1.0
            if person.age < 20:
                assert person.immunity.susceptibility_dict[b117_id] == 1.0
            elif person.age < 40:
                assert person.immunity.susceptibility_dict[b117_id] == 0.25
            else:
                assert person.immunity.susceptibility_dict[b117_id] == 1.0
