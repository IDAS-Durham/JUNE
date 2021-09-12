from june.interaction import Interaction, interaction
from june.epidemiology.infection.infection_selector import InfectionSelector
from june.epidemiology.infection import Immunity
from june.groups import School
from june.demography import Person
from june import paths
from june.geography import Geography
from june.groups.group.interactive import InteractiveGroup
from june.world import generate_world_from_geography
from june.groups import Hospital, Hospitals
from june.epidemiology.infection_seed import InfectionSeed
from june.policy import Policies
from june.simulator import Simulator

import pytest
import numpy as np
import os
import pandas as pd
import pathlib
from itertools import chain

test_config = paths.configs_path / "tests/interaction.yaml"
default_sector_beta_filename = (
    paths.configs_path / "defaults/interaction/sector_beta.yaml"
)


class TestInteractionFunctions:
    def test__contact_matrices_from_default(self):
        interaction = Interaction.from_file(config_filename=test_config)
        np.testing.assert_allclose(
            interaction.contact_matrices["pub"],
            np.array([[3 * (1 + 0.12) * 24 / 3]]),
            rtol=0.05,
        )

    def test__create_infector_tensor(self):
        infectors_per_infection_per_subgroup = {
            1: {2: {"ids": [1, 2, 3], "trans_probs": [0.1, 0.2, 0.3]}},
            2: {
                0: {"ids": [4, 5], "trans_probs": [0.4, 0.5]},
                1: {"ids": [6], "trans_probs": [0.8]},
            },
        }
        subgroup_sizes = [3, 5, 7]
        interaction = Interaction.from_file(config_filename=test_config)
        contact_matrix = np.array([[1, 0, 1], [1, 1, 1], [0, 1, 0]])
        infector_tensor = interaction.create_infector_tensor(
            infectors_per_infection_per_subgroup, subgroup_sizes, contact_matrix, 1, 1
        )
        expected = np.array([[0, 0, 0.6 / 7], [0, 0, 0.6 / 7], [0.0, 0.0, 0.0]])
        assert np.allclose(infector_tensor[1], expected)
        expected = np.array([[0.9 / 2, 0, 0], [0.9 / 3, 0.8 / 4, 0], [0, 0.8 / 5, 0]])
        assert np.allclose(infector_tensor[2], expected)

    def test__gets_infected(self):
        interaction = Interaction.from_file(config_filename=test_config)
        probs = np.array([0.1, 0.2, 0.3])
        possible_infections = [1, 2, 3]
        infections = []
        misses = 0
        n = 10000
        for _ in range(n):
            infection = interaction._gets_infected(probs, possible_infections)
            if infection is None:
                misses += 1
                continue
            infections.append(infection)
        infections = np.array(infections)
        misses_exp = np.exp(-0.6)
        assert np.isclose(misses, misses_exp * n, rtol=0.1)
        assert np.isclose(
            len(infections[infections == 1]), 0.1 / 0.6 * n * (1 - misses_exp), rtol=0.1
        )
        assert np.isclose(
            len(infections[infections == 2]), 0.2 / 0.6 * n * (1 - misses_exp), rtol=0.1
        )
        assert np.isclose(
            len(infections[infections == 3]), 0.3 / 0.6 * n * (1 - misses_exp), rtol=0.1
        )

    def test__blame_subgroup(self):
        interaction = Interaction.from_file(config_filename=test_config)
        probs = np.array([20, 30, 100])
        blames = []
        n = 10000
        for _ in range(n):
            blame = interaction._blame_subgroup(probs)
            blames.append(blame)
        blames = np.array(blames)
        assert np.isclose(len(blames[blames == 0]), 20 / 150 * n, rtol=0.1)
        assert np.isclose(len(blames[blames == 1]), 30 / 150 * n, rtol=0.1)
        assert np.isclose(len(blames[blames == 2]), 100 / 150 * n, rtol=0.1)

    def test__blame_individuals(self):
        interaction = Interaction.from_file(config_filename=test_config)
        infectors_per_infection_per_subgroup = {
            "a": {
                0: {"ids": [1, 2, 3], "trans_probs": [0.1, 0.2, 0.3]},
                1: {"ids": [4], "trans_probs": [0.4]},
            },
            "b": {2: {"ids": [5, 6, 7], "trans_probs": [0.1, 0.2, 0.3]}},
        }
        infection_ids = ["a", "b"]
        to_blame_subgroups = [0, 2]
        blames1 = []
        blames2 = []
        n = 1000
        for i in range(n):
            to_blame_ids = interaction._blame_individuals(
                to_blame_subgroups, infection_ids, infectors_per_infection_per_subgroup
            )
            blames1.append(to_blame_ids[0])
            blames2.append(to_blame_ids[1])
        blames1 = np.array(blames1)
        blames2 = np.array(blames2)
        assert np.isclose(len(blames1[blames1 == 1]), 0.1 / 0.6 * n, rtol=0.1)
        assert np.isclose(len(blames1[blames1 == 2]), 0.2 / 0.6 * n, rtol=0.1)
        assert np.isclose(len(blames1[blames1 == 3]), 0.3 / 0.6 * n, rtol=0.1)
        assert np.isclose(len(blames2[blames2 == 5]), 0.1 / 0.6 * n, rtol=0.1)
        assert np.isclose(len(blames2[blames2 == 6]), 0.2 / 0.6 * n, rtol=0.1)
        assert np.isclose(len(blames2[blames2 == 7]), 0.3 / 0.6 * n, rtol=0.1)


def days_to_infection(interaction, susceptible_person, group, people, n_students):
    delta_time = 1 / 24
    days_to_infection = 0
    while not susceptible_person.infected and days_to_infection < 100:
        for person in people[:n_students]:
            group.subgroups[1].append(person)
        for person in people[n_students:]:
            group.subgroups[0].append(person)
        infected_ids, _, _ = interaction.time_step_for_group(
            group=group, delta_time=delta_time
        )
        if susceptible_person.id in infected_ids:
            break
        days_to_infection += delta_time
        group.clear()
    return days_to_infection


def create_school(n_students, n_teachers):
    school = School(
        n_pupils_max=n_students,
        age_min=6,
        age_max=6,
        coordinates=(1.0, 1.0),
        sector="primary_secondary",
    )
    people = []
    # create students
    for _ in range(n_students):
        person = Person.from_attributes(sex="f", age=6)
        school.add(person)
        people.append(person)
    for _ in range(n_teachers):
        person = Person.from_attributes(sex="m", age=40)
        school.add(person, subgroup_type=school.SubgroupType.teachers)
        people.append(person)
    assert len(people) == n_students + n_teachers
    assert len(school.people) == n_students + n_teachers
    assert len(school.subgroups[1].people) == n_students
    assert len(school.subgroups[0].people) == n_teachers
    return people, school


@pytest.mark.parametrize(
    "n_teachers,mode",
    [
        [2, "average"],
        [4, "average"],
        [6, "average"],
    ],
)
def test__average_time_to_infect(n_teachers, mode, selector):
    selector_config = (
        paths.configs_path / "defaults/transmission/TransmissionConstant.yaml"
    )
    transmission_probability = 0.1
    n_students = 1
    contact_matrices = {
        "contacts": [[n_teachers - 1, 1], [1, 0]],
        "proportion_physical": [
            [
                0,
                0,
            ],
            [0, 0],
        ],
        "xi": 1.0,
        "characteristic_time": 24,
    }
    interaction = Interaction(
        betas={
            "school": 1,
        },
        alpha_physical=1,
        contact_matrices={"school": contact_matrices},
    )
    n_days = []
    for _ in range(100):
        people, school = create_school(n_students, n_teachers)
        for student in people[:n_students]:
            selector.infect_person_at_time(student, time=0)
        for teacher in people[n_students : n_students + n_teachers - 1]:
            selector.infect_person_at_time(teacher, time=0)
        school.clear()
        teacher = people[-1]
        n_days.append(
            days_to_infection(interaction, teacher, school, people, n_students)
        )
    teacher_teacher = transmission_probability * (n_teachers - 1)
    student_teacher = transmission_probability / n_students
    np.testing.assert_allclose(
        np.mean(n_days),
        1.0 / (teacher_teacher + student_teacher),
        rtol=0.1,
    )


def test__infection_is_isolated(epidemiology, selectors):
    geography = Geography.from_file({"area": ["E00002559"]})
    world = generate_world_from_geography(geography, include_households=True)
    interaction = Interaction.from_file(config_filename=test_config)
    infection_seed = InfectionSeed.from_uniform_cases(world, selectors[0], cases_per_capita=5/len(world.people), date="2020-03-01")
    infection_seed.unleash_virus_per_day(date = pd.to_datetime("2020-03-01"), time=0)
    policies = Policies([])
    n_infected = len([person for person in world.people if person.infected])
    simulator = Simulator.from_file(
        world=world,
        interaction=interaction,
        epidemiology=epidemiology,
        config_filename=pathlib.Path(__file__).parent.absolute()
        / "interaction_test_config.yaml",
        leisure=None,
        policies=policies,
        # save_path=None,
    )
    assert np.isclose(n_infected, 5, rtol=0.2)
    infected_households = []
    for household in world.households:
        infected = False
        for person in household.people:
            if person.infected:
                infected = True
                break
        if infected:
            infected_households.append(household)
    assert len(infected_households) <= n_infected
    simulator.run()
    for person in world.people:
        if person.residence is None:
            assert person.dead
        elif not (person.residence.group in infected_households):
            assert not person.infected


def test__super_spreaders(selector):
    people, school = create_school(n_students=5, n_teachers=1000)
    student_ids = [student.id for student in school.students]
    teacher_ids = [teacher.id for teacher in school.teachers]
    transmission_probabilities = np.linspace(0, 30, len(student_ids))
    total = sum(transmission_probabilities)
    id_to_trans = {}
    for i, student in enumerate(school.students):
        selector.infect_person_at_time(student, time=0)
        student.infection.transmission.probability = transmission_probabilities[i]
        id_to_trans[student.id] = transmission_probabilities[i]
    interactive_school = school.get_interactive_group()
    interaction = Interaction.from_file(config_filename=test_config)
    beta = interaction._get_interactive_group_beta(interactive_school)
    contact_matrix_raw = interaction.contact_matrices["school"]
    contact_matrix = interactive_school.get_processed_contact_matrix(contact_matrix_raw)
    infector_tensor = interaction.create_infector_tensor(
        interactive_school.infectors_per_infection_per_subgroup,
        interactive_school.subgroup_sizes,
        contact_matrix,
        beta,
        delta_time=1,
    )
    (
        subgroup_infected_ids,
        subgroup_infection_ids,
        to_blame_subgroups,
    ) = interaction._time_step_for_subgroup(
        infector_tensor=infector_tensor,
        susceptible_subgroup_id=0,
        subgroup_susceptibles=interactive_school.susceptibles_per_subgroup[0],
    )
    to_blame_ids = interaction._blame_individuals(
        to_blame_subgroups,
        subgroup_infection_ids,
        interactive_school.infectors_per_infection_per_subgroup,
    )
    for id in subgroup_infected_ids:
        assert id in teacher_ids
    for id in to_blame_ids:
        assert id in student_ids
    n_infections = len(subgroup_infected_ids)
    assert n_infections > 0
    culpable_ids, culpable_counts = np.unique(to_blame_ids, return_counts=True)
    for culpable_id, culpable_count in zip(culpable_ids, culpable_counts):
        expected = (id_to_trans[culpable_id] / total * n_infections,)
        assert np.isclose(
            culpable_count,
            expected,
            rtol=0.25,
        )
