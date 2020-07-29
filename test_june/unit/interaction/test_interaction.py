from june.interaction import Interaction, interaction
from june.infection.infection import InfectionSelector
from june.groups import School
from june.demography import Person
from june import paths
from june.demography.geography import Geography
from june.interaction.interactive_group import InteractiveGroup
from june.world import generate_world_from_geography
from june.groups import Hospital, Hospitals
from june.infection_seed import InfectionSeed
from june.policy import Policies
from june.simulator import Simulator

import pytest
import numpy as np
import os
import pathlib

test_config = paths.configs_path / "defaults/interaction/ContactInteraction.yaml"


def test__contact_matrices_from_default():
    interaction = Interaction.from_file(config_filename=test_config)
    np.testing.assert_allclose(
        interaction.contact_matrices["pub"],
        np.array([[3 * (1 + 0.12) * 24 / 3]]),
        rtol=0.05,
    )
    xi = 0.3
    contacts_school = interaction.contact_matrices["school"]
    for i in range(len(contacts_school)):
        for j in range(len(contacts_school)):
            if i == j:
                if i == 0:
                    assert contacts_school[i][j] == 5.25 * 3  # 24 / 8
                else:
                    assert contacts_school[i][j] == 2.875 * 3
            else:
                if i == 0:
                    assert np.isclose(contacts_school[i][j], 16.2 * 3, rtol=1e-6)
                elif j == 0:
                    assert np.isclose(
                        contacts_school[i][j], 0.81 * 3, atol=0, rtol=1e-6
                    )
                else:
                    assert np.isclose(
                        contacts_school[i][j],
                        xi ** abs(i - j) * 2.875 * 3,
                        atol=0,
                        rtol=1e-6,
                    )


def test__school_index_translation():
    age_min = 3
    age_max = 7
    school_years = tuple(range(age_min, age_max + 1))
    interaction._translate_school_subgroup(1, school_years) == 4
    interaction._translate_school_subgroup(5, school_years) == 8


def test__school_contact_matrices():
    interaction_instance = Interaction.from_file()
    xi = 0.3
    age_min = 3
    age_max = 7
    school_years = tuple(range(age_min, age_max + 1))
    contact_matrix = interaction_instance.contact_matrices["school"]
    n_contacts_same_year = interaction._get_contacts_in_school(
        contact_matrix, school_years, 4, 4
    )
    assert n_contacts_same_year == 2.875 * 3

    n_contacts_year_above = interaction._get_contacts_in_school(
        contact_matrix, school_years, 4, 5
    )
    assert n_contacts_year_above == xi * 2.875 * 3

    n_contacts_teacher_teacher = interaction._get_contacts_in_school(
        contact_matrix, school_years, 0, 0
    )
    assert n_contacts_teacher_teacher == 5.25 * 3

    n_contacts_teacher_student = interaction._get_contacts_in_school(
        contact_matrix, school_years, 0, 4
    )
    np.isclose(n_contacts_teacher_student, (16.2 * 3 / len(school_years)), rtol=1e-6)

    n_contacts_student_teacher = interaction._get_contacts_in_school(
        contact_matrix, school_years, 4, 0
    )
    assert n_contacts_student_teacher == 0.81 * 3


def days_to_infection(interaction, susceptible_person, group, people, n_students):
    delta_time = 1 / 24
    days_to_infection = 0
    while not susceptible_person.infected and days_to_infection < 100:
        for person in people[:n_students]:
            group.subgroups[1].append(person)
        for person in people[n_students:]:
            group.subgroups[0].append(person)
        interactive_group = InteractiveGroup(group)
        infected_ids = interaction.time_step_for_group(
            group=interactive_group, delta_time=delta_time
        )
        if infected_ids:
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
    "n_teachers,mode", [[2, "average"], [4, "average"], [6, "average"],],
)
def test__average_time_to_infect(n_teachers, mode):
    selector_config = paths.configs_path / "defaults/infection/InfectionConstant.yaml"
    transmission_probability = 0.1
    selector = InfectionSelector.from_file(config_filename=selector_config)
    n_students = 1
    contact_matrices = {
        "contacts": [[n_teachers - 1, 1], [1, 0]],
        "proportion_physical": [[0, 0,], [0, 0]],
        "xi": 1.0,
        "characteristic_time": 24,
    }
    interaction = Interaction(
        beta={"school": 1,},
        alpha_physical=1,
        contact_matrices={"school": contact_matrices},
    )
    n_days = []
    for _ in range(200):
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
        np.mean(n_days), 1.0 / (teacher_teacher + student_teacher), rtol=0.1,
    )


def test__infection_is_isolated(selector):
    geography = Geography.from_file({"area": ["E00002559"]})
    world = generate_world_from_geography(geography, include_households=True)
    interaction = Interaction.from_file()
    infection_seed = InfectionSeed(world.super_areas, selector)
    n_cases = 5
    infection_seed.unleash_virus(
        n_cases
    )  # play around with the initial number of cases
    policies = Policies([])
    simulator = Simulator.from_file(
        world=world,
        interaction=interaction,
        infection_selector=selector,
        config_filename=pathlib.Path(__file__).parent.absolute()
        / "interaction_test_config.yaml",
        leisure=None,
        policies=policies,
        save_path=None,
    )
    infected_people = [person for person in world.people if person.infected]
    assert len(infected_people) == 5
    infected_households = []
    for household in world.households:
        infected = False
        for person in household.people:
            if person.infected:
                infected = True
                break
        if infected:
            infected_households.append(household)
    simulator.run()
    for person in world.people:
        if person.residence.group in infected_households:
            assert person.infected or not person.susceptible
        else:
            assert not person.infected and person.susceptible
