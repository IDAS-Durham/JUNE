from june.interaction import Interaction, interaction
from june.infection.infection_selector import InfectionSelector
from june.groups import School
from june.demography import Person
from june import paths
from june.geography import Geography
from june.groups.group.interactive import InteractiveGroup
from june.world import generate_world_from_geography
from june.groups import Hospital, Hospitals
from june.infection_seed import InfectionSeed
from june.policy import Policies
from june.simulator import Simulator

import pytest
import numpy as np
import os
import pathlib
from itertools import chain

test_config = paths.configs_path / "tests/interaction.yaml"
default_sector_beta_filename = (
    paths.configs_path / "defaults/interaction/sector_beta.yaml"
)


def test__contact_matrices_from_default():
    interaction = Interaction.from_file(config_filename=test_config)
    np.testing.assert_allclose(
        interaction.contact_matrices["pub"],
        np.array([[3 * (1 + 0.12) * 24 / 3]]),
        rtol=0.05,
    )


def days_to_infection(interaction, susceptible_person, group, people, n_students):
    delta_time = 1 / 24
    days_to_infection = 0
    while not susceptible_person.infected and days_to_infection < 100:
        for person in people[:n_students]:
            group.subgroups[1].append(person)
        for person in people[n_students:]:
            group.subgroups[0].append(person)
        infected_ids, group_size = interaction.time_step_for_group(
            group=group, delta_time=delta_time
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
    selector_config = (
        paths.configs_path / "defaults/transmission/TransmissionConstant.yaml"
    )
    transmission_probability = 0.1
    selector = InfectionSelector.from_file(transmission_config_path=selector_config)
    n_students = 1
    contact_matrices = {
        "contacts": [[n_teachers - 1, 1], [1, 0]],
        "proportion_physical": [[0, 0,], [0, 0]],
        "xi": 1.0,
        "characteristic_time": 24,
    }
    interaction = Interaction(
        betas={"school": 1,},
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
    interaction = Interaction.from_file(config_filename=test_config)
    infection_seed = InfectionSeed(world, selector)
    n_cases = 5
    infection_seed.unleash_virus(
        world.people, n_cases=n_cases
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
        # save_path=None,
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
    assert len(infected_households) <= 5
    simulator.run()
    for person in world.people:
        if person.residence is None:
            assert person.dead
        elif not (person.residence.group in infected_households):
            assert not person.infected and person.susceptible


def test__assign_blame():
    interaction = Interaction.from_file(config_filename=test_config)
    transmission_weights = [1, 10, 2, 3, 4]
    transmission_ids = [0, 1, 4, 5, 6]
    total_wegiht = sum(transmission_weights)
    n_infections = 5000
    culpables = interaction._assign_blame_for_infections(
        n_infections, transmission_weights, transmission_ids
    )
    culpable_ids, culpable_counts = np.unique(culpables, return_counts=True)
    culpable_counts = {key: value for key, value in zip(culpable_ids, culpable_counts)}
    for trans_id, trans_weight in zip(transmission_ids, transmission_weights):
        assert np.isclose(
            culpable_counts[trans_id],
            n_infections * trans_weight / total_wegiht,
            rtol=0.05,
        )
