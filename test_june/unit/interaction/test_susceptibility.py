import pytest
import numpy as np
from random import randint

from june.utils import parse_age_probabilities
from june.interaction import Interaction
from june.demography import Population, Person
from june.groups import Company
from june.epidemiology.infection import Infection, TransmissionConstant


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
            infected_ids, _, group_size = interaction.time_step_for_group(
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

    def test__run_different_susceptibility(self, simulation_setup):
        group, population = simulation_setup
        interaction = Interaction(
            betas={"company": 1},
            alpha_physical=1.0,
            contact_matrices=None,
        )
        for person in population:
            if person.age < 13:
                person.immunity.susceptibility_dict[Infection.infection_id()] = 0.5
        n_kids_inf, n_adults_inf = self.run_interaction(
            interaction=interaction, simulation_setup=simulation_setup
        )
        assert n_kids_inf > 0
        assert n_adults_inf > 0
        assert np.isclose(0.5 * n_kids_inf, n_adults_inf, rtol=0.05)
