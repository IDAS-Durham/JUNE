from june.interaction.contact_averaging import ContactAveraging
from june.interaction.contact_sampling import ContactSampling
from june.infection.infection import InfectionSelector
from june.groups import School
from june.demography import Person
from june import paths

import pytest
import numpy as np


def days_to_infection(interaction, susceptible_person, group):
    delta_time = 0.25
    days_to_infection = 0
    while not susceptible_person.infected and days_to_infection < 100:
        interaction.single_time_step_for_group(
            group, days_to_infection, delta_time, logger=None
        )
        days_to_infection += delta_time

    return days_to_infection


@pytest.mark.parametrize(
    "n_teachers,mode",
    [
        [2, "average"],
        [2, "sampling"],
        [4, "average"],
        [4, "sampling"],
        [6, "average"],
        [6, "sampling"],
    ],
)
def test__average_time_to_infect(n_teachers, mode):
    selector_config = paths.configs_path / "defaults/infection/InfectionConstant.yaml"
    selector = InfectionSelector.from_file(selector_config)
    n_students = 1
    if mode == "average":
        interaction = ContactAveraging(
            betas={"school": 1,},
            contact_matrices={"school": [[n_teachers - 1, 1], [1, 0]]},
            selector=selector,
        )
    elif mode == "sampling":
        interaction = ContactSampling(
            betas={"school": 1,},
            contact_matrices={"school": [[n_teachers - 1, 1], [1, 0]]},
            selector=selector,
        )
    n_days = []
    for n in range(1000):
        school = School(
            n_pupils_max=n_students,
            n_teachers_max=n_teachers,
            age_min=6,
            age_max=6,
            coordinates=(1.0, 1.0),
            sector="primary_secondary",
        )
        for student in range(n_students):
            student = Person.from_attributes(sex="f", age=6)
            school.add(student)
            selector.infect_person_at_time(student, time=0)
        for teacher in range(n_teachers - 1):
            teacher = Person.from_attributes(sex="m", age=40)
            school.add(teacher, subgroup_type=school.SubgroupType.teachers)
            selector.infect_person_at_time(teacher, time=0)
        teacher = Person.from_attributes(sex="m", age=40)
        school.add(teacher, subgroup_type=school.SubgroupType.teachers)
        n_days.append(days_to_infection(interaction, teacher, school))
    teacher_teacher = interaction.selector.transmission_probability * (n_teachers - 1)
    student_teacher = interaction.selector.transmission_probability / n_students
    np.testing.assert_allclose(
        np.mean(n_days), 1.0 / (teacher_teacher + student_teacher), rtol=0.1,
    )
