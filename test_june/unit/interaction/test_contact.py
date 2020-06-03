from june.interaction.contact_averaging import ContactAveraging
from june.interaction.contact_sampling import ContactSampling
from june.infection.infection import InfectionSelector
from june.groups import School
from june.demography import Person
from june import paths

import pytest
import numpy as np

test_config = paths.configs_path / "tests/contact_interaction.yaml"
def test__contact_matrices_from_default():
    interaction = ContactAveraging.from_file(config_filename= test_config,
            selector=None)
    assert interaction.contact_matrices['pub'] == np.array([[1]])
    xi = 0.3
    contacts_school = interaction.contact_matrices['school']
    for i in range(len(contacts_school)):
        for j in range(len(contacts_school)):
            if i == j:
                if i == 0:
                    assert contacts_school[i][j] == 25
                else:
                    assert contacts_school[i][j] == 2.5 
            else:
                if i == 0: 
                    assert contacts_school[i][j] == 0.75 
                elif j == 0:
                    assert contacts_school[i][j] == 15
                else:
                    assert contacts_school[i][j] == xi**abs(i-j)*2.5

def test__school_index_translation():
    interaction = ContactAveraging.from_file(selector=None)
    age_min = 3
    age_max = 7
    school_years = list(range(age_min, age_max+1))
    interaction.translate_school_subgroup(1, school_years) == 4
    interaction.translate_school_subgroup(5, school_years) == 8


def days_to_infection(interaction, susceptible_person, group, people, n_students):
    delta_time = 0.1
    days_to_infection = 0
    while not susceptible_person.infected and days_to_infection < 100:
        for person in people[:n_students]:
            group.subgroups[1].append(person)
        for person in people[n_students:]:
            group.subgroups[0].append(person)
        interaction.single_time_step_for_group(
            group, days_to_infection, delta_time, logger=None
        )
        days_to_infection += delta_time
        group.clear()

    return days_to_infection

def create_school(n_students, n_teachers):
    school = School(
            n_pupils_max=n_students,
            age_min=6,
            age_max=6,
        coordinates=(1.0,1.0),
        sector='primary_secondary',
    )
    people = []
    # create students
    for student in range(n_students):
        person = Person.from_attributes(sex='f', age=6)
        school.add(person)
        people.append(person)
    for teacher in range(n_teachers):
        person = Person.from_attributes(sex='m', age=40)
        school.add(person,
                  subgroup_type=school.SubgroupType.teachers)
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
        #[2, "sampling"],
        [4, "average"],
        #[4, "sampling"],
        [6, "average"],
        #[6, "sampling"],
    ],
)
def test__average_time_to_infect(n_teachers, mode):
    selector_config = paths.configs_path / "defaults/infection/InfectionConstant.yaml"
    selector = InfectionSelector.from_file(selector_config)
    n_students = 1
    contact_matrices = {'contacts': [[n_teachers-1, 1], [1,0]],
                        'proportion_physical': [[1,1,],[1,1]],
                        'xi': 1.}
    if mode == "average":
        interaction = ContactAveraging(
            beta={"school": 1,},
            alpha_physical = 1,
            selector=selector,
            contact_matrices = {'school': contact_matrices},
        )
    elif mode == "sampling":
        interaction = ContactSampling(
            betas={"school": 1,},
            alphas = {'school':1,},
            selector=selector,
        )
    n_days = []
    for _ in range(1000):
        people, school = create_school(n_students, n_teachers)
        for student in people[:n_students]:
            selector.infect_person_at_time(student, time=0)
        for teacher in people[n_students:n_students+n_teachers-1]:
            selector.infect_person_at_time(teacher, time=0)
        school.clear()
        teacher = people[-1]
        n_days.append(days_to_infection(interaction, teacher, school, people, n_students))
    teacher_teacher = interaction.selector.transmission_probability * (n_teachers - 1)
    student_teacher = interaction.selector.transmission_probability / n_students
    print(interaction.selector.transmission_probability)
    np.testing.assert_allclose(
        np.mean(n_days), 1.0 / (teacher_teacher + student_teacher), rtol=0.1,
    )
