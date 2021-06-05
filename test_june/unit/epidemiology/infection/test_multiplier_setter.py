import pytest

from june.utils import parse_age_probabilities
from june.epidemiology.infection import Covid19, B117, EffectiveMultiplierSetter
from june.demography import Person, Population


@pytest.fixture(name="multiplier_dict")
def make_multiplier():
    return {
        Covid19.infection_id(): 1.,
        B117.infection_id(): 1.5,
    }

class TestMultiplierSetter:

    def test__multiplier_variants_setter(self, multiplier_dict):
        population = Population([])
        for i in range(105):
            population.add(Person.from_attributes(age=i))

        multiplier_setter = EffectiveMultiplierSetter(multiplier_dict)
        multiplier_setter.set_multipliers(population)
        c19_id = Covid19.infection_id()
        b117_id = B117.infection_id()

        for person in population:
            assert person.immunity.effective_multiplier_dict[c19_id] == 1.
            assert person.immunity.effective_multiplier_dict[b117_id] == 1.5
