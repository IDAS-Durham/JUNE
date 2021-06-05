import pytest
import numpy as np
from random import randint

from june.utils import (
    parse_age_probabilities,
    parse_prevalence_comorbidities_in_reference_population,
)
from june.interaction import Interaction
from june.demography import Population, Person
from june.groups import Company
from june.epidemiology.infection import Infection, TransmissionConstant


class TestInteractionChangesMultipliers:
    def test__parse_inputs(
        self,
    ):
        pass

    def test__mean_multiplier_reference(
        self,
    ):
        interaction = Interaction(
            betas=None,
            alpha_physical=None,
            contact_matrices=None,
            susceptibilities_by_age=None,
            population=None,
        )

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
        interaction.multiplier_by_comorbidity = comorbidity_multipliers
        interaction.comorbidity_prevalence_reference_population = (
            prevalence_reference_population
        )
        interaction.comorbidity_prevalence_reference_population = (
            parse_prevalence_comorbidities_in_reference_population(
                prevalence_reference_population
            )
        )
        print(prevalence_reference_population)
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
            interaction.get_multiplier_from_reference_prevalence(dummy.age, dummy.sex)
            == mean_multiplier_uk
        )
    
    def test__interaction_changes_multiplier(self,):
        comorbidity_multipliers = {"guapo": 0.8, "feo": 1.2, "no_condition": 1.0}
        population = Population([])
        for comorbidity in comorbidity_multipliers.keys():
            population.add(Person.from_attributes(age=40,comorbidity=comorbidity))
        for person in population:
            assert person.effective_multiplier == 1.
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

        interaction = Interaction(
            betas=None,
            alpha_physical=None,
            contact_matrices=None,
            multiplier_by_comorbidity=comorbidity_multipliers,
            comorbidity_prevalence_reference_population=comorbidity_prevalence_reference_population,
            population=population,
        )
        assert population[0].effective_multiplier == 0.8
        assert population[1].effective_multiplier == 1.2
        assert population[2].effective_multiplier == 1.


