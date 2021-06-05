import pytest

from june.utils import (
    parse_age_probabilities,
    parse_prevalence_comorbidities_in_reference_population,
)


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

    def test__mean_multiplier_reference(
        self,
    ):
        prevalence_reference_population = {
            "feo": {
                "f": {"0-10": 0.2, "10-100": 0.4},
                "m": {"0-10": 0.6, "10-100": 0.5},
            },
            "guapo": {
                "f": {"0-10": 0.1, "10-100": 0.1},
                "m": {"0-10": 0.05, "10-100": 0.2},
            },
            "no_condition": {
                "f": {"0-10": 0.7, "10-100": 0.5},
                "m": {"0-10": 0.35, "10-100": 0.3},
            },
        }
        comorbidity_multipliers = {"guapo": 0.8, "feo": 1.2, "no_condition": 1.0}
        multiplier_setter = EffectiveMultiplierSetter(
                multiplier_by_comorbidity = comorbidity_multipliers,
                comorbidity_prevalence_reference_population=prevalence_reference_population
        )
        dummy = Person.from_attributes(
            sex="f",
            age=40,
        )
        mean_multiplier_uk = (
            prevalence_reference_population["feo"]["f"]["10-100"]
            * comorbidity_multipliers["feo"]
            + prevalence_reference_population["guapo"]["f"]["10-100"]
            * comorbidity_multipliers["guapo"]
            + prevalence_reference_population["no_condition"]["f"]["10-100"]
            * comorbidity_multipliers["no_condition"]
        )
        assert (
            multiplier_setter.get_multiplier_from_reference_prevalence(dummy.age, dummy.sex)
            == mean_multiplier_uk
        )

    def test__interaction_changes_multiplier(self,):
        c19_id = Covid19.infection_id()
        b117_id = B117.infection_id()
        comorbidity_multipliers = {"guapo": 0.8, "feo": 1.2, "no_condition": 1.0}
        population = Population([])
        for comorbidity in comorbidity_multipliers.keys():
            population.add(Person.from_attributes(age=40,comorbidity=comorbidity))
        for person in population:
            assert person.immunity.effective_multiplier_dict[c19_id] == 1.
            assert person.immunity.effective_multiplier_dict[b117_id] == 1.
        comorbidity_prevalence_reference_population = {
            "guapo": {
                "f": {"0-100": 0.},
                "m": {"0-100": 0.},
            },
            "feo": {
                "f": {"0-100": 0.},
                "m": {"0-100": 0.},
            },
            "no_condition": {
                "m": {"0-100": 1.},
                "f": {"0-100": 1.},
            },
        }

        multiplier_setter = EffectiveMultiplierSetter(
                multiplier_by_comorbidity = comorbidity_multipliers,
                comorbidity_prevalence_reference_population=comorbidity_prevalence_reference_population,
        )
        multiplier_setter.set_multipliers(population)
        assert population[0].immunity.effective_multiplier_dict[c19_id] == 0.8
        assert population[0].immunity.effective_multiplier_dict[b117_id] == 1.3 

        assert population[1].immunity.effective_multiplier_dict[c19_id] == 1.2
        assert population[1].immunity.effective_multiplier_dict[b117_id] == 1.7 

        assert population[2].immunity.effective_multiplier_dict[c19_id] == 1.
        assert population[2].immunity.effective_multiplier_dict[b117_id] == 1.5

