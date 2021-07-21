import pytest
import numpy as np

from june.utils import (
    parse_age_probabilities,
    parse_prevalence_comorbidities_in_reference_population,
)


from june.epidemiology.infection import Covid19, B117, ImmunitySetter
from june.demography import Person, Population


@pytest.fixture(name="susceptibility_dict")
def make_susc():
    return {
        Covid19.infection_id(): {"0-13": 0.5, "13-100": 1.0},
        B117.infection_id(): {"20-40": 0.25},
    }


class TestSusceptibilitySetter:
    def test__susceptibility_parser(self, susceptibility_dict):
        susc_setter = ImmunitySetter(susceptibility_dict)
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

    def test__susceptiblity_setter_average(self, susceptibility_dict):
        population = Population([])
        for i in range(105):
            population.add(Person.from_attributes(age=i))

        susceptibility_setter = ImmunitySetter(susceptibility_dict)
        susceptibility_setter.set_susceptibilities(population)
        c19_id = Covid19.infection_id()
        b117_id = B117.infection_id()

        for person in population:
            if person.age < 13:
                assert person.immunity.get_susceptibility(c19_id) == 0.5
            else:
                assert person.immunity.get_susceptibility(c19_id) == 1.0
            if person.age < 20:
                assert person.immunity.get_susceptibility(b117_id) == 1.0
            elif person.age < 40:
                assert person.immunity.get_susceptibility(b117_id) == 0.25
            else:
                assert person.immunity.get_susceptibility(b117_id) == 1.0

    def test__susceptiblity_setter_individual(self, susceptibility_dict):
        population = Population([])
        for i in range(105):
            for j in range(10):
                population.add(Person.from_attributes(age=i))

        susceptibility_setter = ImmunitySetter(
            susceptibility_dict, susceptibility_mode="individual"
        )
        susceptibility_setter.set_susceptibilities(population)
        c19_id = Covid19.infection_id()
        b117_id = B117.infection_id()
        immune_c19_13 = 0
        immune_b117_13 = 0
        immune_40 = 0
        for person in population:
            if person.age < 13:
                if person.immunity.get_susceptibility(c19_id) == 0.0:
                    immune_c19_13 += 1
                if person.immunity.get_susceptibility(b117_id) == 0.0:
                    immune_b117_13 += 1
            if person.age < 20:
                assert person.immunity.get_susceptibility(b117_id) == 1.0
            elif person.age < 40:
                if person.immunity.get_susceptibility(b117_id) == 0.0:
                    immune_40 += 1
            else:
                assert person.immunity.get_susceptibility(b117_id) == 1.0
        aged_13 = len([person for person in population if person.age < 13])
        aged_40 = len([person for person in population if 20 <= person.age < 40])
        assert np.isclose(immune_c19_13 / aged_13, 0.5, rtol=1e-1)
        assert immune_b117_13 == 0
        assert np.isclose(immune_40 / aged_40, 0.75, rtol=1e-1)


@pytest.fixture(name="multiplier_dict")
def make_multiplier():
    return {
        Covid19.infection_id(): 1.0,
        B117.infection_id(): 1.5,
    }


class TestMultiplierSetter:
    def test__multiplier_variants_setter(self, multiplier_dict):
        population = Population([])
        for i in range(105):
            population.add(Person.from_attributes(age=i))

        multiplier_setter = ImmunitySetter(multiplier_dict=multiplier_dict)
        multiplier_setter.set_multipliers(population)
        c19_id = Covid19.infection_id()
        b117_id = B117.infection_id()

        for person in population:
            assert person.immunity.get_effective_multiplier(c19_id) == 1.0
            assert person.immunity.get_effective_multiplier(b117_id) == 1.5

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
        multiplier_setter = ImmunitySetter(
            multiplier_by_comorbidity=comorbidity_multipliers,
            comorbidity_prevalence_reference_population=prevalence_reference_population,
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
            multiplier_setter.get_multiplier_from_reference_prevalence(
                dummy.age, dummy.sex
            )
            == mean_multiplier_uk
        )

    def test__interaction_changes_multiplier(
        self,
    ):
        c19_id = Covid19.infection_id()
        b117_id = B117.infection_id()
        comorbidity_multipliers = {"guapo": 0.8, "feo": 1.2, "no_condition": 1.0}
        population = Population([])
        for comorbidity in comorbidity_multipliers.keys():
            population.add(Person.from_attributes(age=40, comorbidity=comorbidity))
        for person in population:
            assert person.immunity.get_effective_multiplier(c19_id) == 1.0
            assert person.immunity.get_effective_multiplier(b117_id) == 1.0
        comorbidity_prevalence_reference_population = {
            "guapo": {
                "f": {"0-100": 0.0},
                "m": {"0-100": 0.0},
            },
            "feo": {
                "f": {"0-100": 0.0},
                "m": {"0-100": 0.0},
            },
            "no_condition": {
                "m": {"0-100": 1.0},
                "f": {"0-100": 1.0},
            },
        }

        multiplier_setter = ImmunitySetter(
            multiplier_by_comorbidity=comorbidity_multipliers,
            comorbidity_prevalence_reference_population=comorbidity_prevalence_reference_population,
        )
        multiplier_setter.set_multipliers(population)
        assert population[0].immunity.effective_multiplier_dict[c19_id] == 0.8
        assert population[0].immunity.effective_multiplier_dict[b117_id] == 1.3

        assert population[1].immunity.effective_multiplier_dict[c19_id] == 1.2
        assert population[1].immunity.effective_multiplier_dict[b117_id] == 1.7

        assert population[2].immunity.effective_multiplier_dict[c19_id] == 1.0
        assert population[2].immunity.effective_multiplier_dict[b117_id] == 1.5
