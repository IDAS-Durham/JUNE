import pytest
import numpy as np
from random import randint

from june.utils import parse_age_probabilities
from june.interaction import Interaction
from june.demography import Population, Person
from june.groups import Company
from june.infection import Infection, TransmissionConstant


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
            betas=None,
            alpha_physical=None,
            contact_matrices=None,
            susceptibilities_by_age=susceptibility_dict,
            population=population,
        )
        for person in population:
            if person.age < 13:
                assert person.susceptibility == 0.5
            else:
                assert person.susceptibility == 1.0


class TestSusceptibilityHasAnEffect:
    @pytest.fixture(name="simulation_setup")
    def setup_group(self):
        company = Company()
        population = Population([])
        n_kids = 50
        n_adults = 50
        for _ in range(n_kids):
            population.add(Person.from_attributes(age=randint(0, 12)))
        for _ in range(n_adults):
            population.add(Person.from_attributes(age=randint(13, 100)))
        for person in population:
            company.add(person)
        # infect one kid and one adult
        kid = population[0]
        assert kid.age <= 12
        adult = population[-1]
        assert adult.age >= 13
        kid.infection = Infection(
            symptoms=None, transmission=TransmissionConstant(probability=0.2)
        )
        adult.infection = Infection(
            symptoms=None, transmission=TransmissionConstant(probability=0.2)
        )
        return company, population

    def run_interaction(self, simulation_setup, interaction):
        """
        With uniform susc. number of infected adults and kids should be the same.
        """
        group, population = simulation_setup
        n_infected_adults_list = []
        n_infected_kids_list = []
        for _ in range(1000):
            infected_ids, group_size = interaction.time_step_for_group(
                group=group, delta_time=10
            )
            n_infected_adults = len(
                [
                    person
                    for person in population
                    if person.id in infected_ids and person.age <= 12
                ]
            )
            n_infected_kids = len(
                [
                    person
                    for person in population
                    if person.id in infected_ids and person.age > 12
                ]
            )
            n_infected_adults_list.append(n_infected_adults)
            n_infected_kids_list.append(n_infected_kids)
        return np.mean(n_infected_kids_list), np.mean(n_infected_adults_list)

    def test__run_uniform_susceptibility(self, simulation_setup):
        contact_matrices = {
            "company": {
                "contacts": [[1]],
                "proportion_physical": [[1]],
                "characteristic_time": 8,
            }
        }
        interaction = Interaction(
            betas={"company": 1}, alpha_physical=1.0, contact_matrices=contact_matrices
        )
        n_kids_inf, n_adults_inf = self.run_interaction(
            interaction=interaction, simulation_setup=simulation_setup
        )
        assert n_kids_inf > 0
        assert n_adults_inf > 0
        assert np.isclose(n_kids_inf, n_adults_inf, rtol=0.05)

    def test__run_different_susceptibility(self, simulation_setup, susceptibility_dict):
        group, population = simulation_setup
        interaction = Interaction(
            betas={"company": 1},
            alpha_physical=1.0,
            contact_matrices=None,
            susceptibilities_by_age=susceptibility_dict,
            population=population,
        )
        n_kids_inf, n_adults_inf = self.run_interaction(
            interaction=interaction, simulation_setup=simulation_setup
        )
        assert n_kids_inf > 0
        assert n_adults_inf > 0
        assert np.isclose(0.5 * n_kids_inf, n_adults_inf, rtol=0.05)
