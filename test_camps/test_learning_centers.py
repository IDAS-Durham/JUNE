import numpy as np
from sklearn.neighbors import BallTree

from june.demography import Person, Population
from june.time import Timer
from june.world import World
from june.groups import *
from june.policy import Policies

from camps.groups import LearningCenter, LearningCenters
from camps.activity import CampActivityManager


def make_dummy_world():
    teacher = Person.from_attributes(age=100, sex="f")
    pupil_shift_1 = Person.from_attributes(age=12, sex="f")
    pupil_shift_2 = Person.from_attributes(age=5, sex="m")
    pupil_shift_3 = Person.from_attributes(age=11, sex="f")
    learning_center = LearningCenter(coordinates=None, n_pupils_max=None)
    household = Household()
    household.add(person=teacher)
    household.add(person=pupil_shift_1)
    household.add(person=pupil_shift_2)
    household.add(person=pupil_shift_3)
    learning_center.add(
        person=teacher, shift=0, subgroup_type=learning_center.SubgroupType.teachers
    )
    learning_center.add(
        person=teacher, shift=1, subgroup_type=learning_center.SubgroupType.teachers
    )
    learning_center.add(
        person=teacher, shift=2, subgroup_type=learning_center.SubgroupType.teachers
    )
    learning_center.add(person=pupil_shift_1, shift=0)
    learning_center.add(person=pupil_shift_2, shift=1)
    learning_center.add(person=pupil_shift_3, shift=2)
    world = World()
    world.learning_centers = LearningCenters([learning_center],learning_centers_tree=False)
    world.households = Households([household])
    world.people = Population([teacher,pupil_shift_1, pupil_shift_2, pupil_shift_3])
    for person in world.people.members:
        person.busy = False
    learning_center.clear()
    household.clear()
    return (
        teacher,
        pupil_shift_1,
        pupil_shift_2,
        pupil_shift_3,
        learning_center,
        household,
        world,
    )


def make_dummy_activity_manager(world):
    timer = Timer(
        total_days=10,
        weekday_step_duration=[8, 8, 8],
        weekend_step_duration=[8, 8, 8],
        weekday_activities=[
            ["primary_activity", "residence"],
            ["primary_activity", "residence"],
        ],
        weekend_activities=[
            ["primary_activity", "residence"],
            ["primary_activity", "residence"],
        ],
    )
    activity_manager = CampActivityManager(
        world=world,
        policies=Policies.from_file(),
        timer=timer,
        all_activities=["primary_activity", "residence"],
        activity_to_groups={
            "primary_activity": ["learning_centers"],
            "residence": ["households"],
        },
    )
    return activity_manager


def test__activate_next_shift():

    (
        teacher,
        pupil_shift_1,
        pupil_shift_2,
        pupil_shift_3,
        learning_center,
        household,
        world,
    ) = make_dummy_world()
    activity_manager = make_dummy_activity_manager(world)
    assert learning_center.active_shift == 0
    activity_manager.activate_next_shift()
    assert learning_center.active_shift == 1
    activity_manager.activate_next_shift()
    assert learning_center.active_shift == 2
    activity_manager.activate_next_shift()
    assert learning_center.active_shift == 0


def test__shift_manager_moving_people():
    (
        teacher,
        pupil_shift_1,
        pupil_shift_2,
        pupil_shift_3,
        learning_center,
        _,
        world,
    ) = make_dummy_world()
    activity_manager = make_dummy_activity_manager(world)
    assert teacher.id in learning_center.ids_per_shift[0]
    assert teacher.id in learning_center.ids_per_shift[1]
    assert teacher.id in learning_center.ids_per_shift[2]
    assert pupil_shift_1.id in learning_center.ids_per_shift[0]
    assert pupil_shift_2.id in learning_center.ids_per_shift[1]
    assert pupil_shift_3.id in learning_center.ids_per_shift[2]
    activity_manager.do_timestep()

    assert teacher in learning_center.people
    assert pupil_shift_1 in learning_center.people
    assert pupil_shift_2 not in learning_center.people
    assert pupil_shift_3 not in learning_center.people
    assert len(learning_center.people) == 2

    learning_center.clear()
    for person in world.people.members:
        person.busy = False
    activity_manager.do_timestep()

    assert teacher in learning_center.people
    assert pupil_shift_1 not in learning_center.people
    assert pupil_shift_2 in learning_center.people
    assert pupil_shift_3 not in learning_center.people
    assert len(learning_center.people) == 2

    learning_center.clear()
    for person in world.people.members:
        person.busy = False
    activity_manager.do_timestep()
    assert teacher in learning_center.people
    assert pupil_shift_1 not in learning_center.people
    assert pupil_shift_2 not in learning_center.people
    assert pupil_shift_3 in learning_center.people
    assert len(learning_center.people) == 2

    learning_center.clear()
    for person in world.people.members:
        person.busy = False
    activity_manager.do_timestep()
    assert teacher in learning_center.people
    assert pupil_shift_1 in learning_center.people
    assert pupil_shift_2 not in learning_center.people
    assert pupil_shift_3 not in learning_center.people
    assert len(learning_center.people) == 2


def test__get_closest_learning_center():

    coordinates_1 = (12.3, 15.6)
    learning_center_1 = LearningCenter(coordinates=coordinates_1, n_pupils_max=20)
    coordinates_2 = (120.3, 150.6)
    learning_center_2 = LearningCenter(coordinates=coordinates_2, n_pupils_max=20)
    learning_centers = LearningCenters(
        learning_centers=[learning_center_1, learning_center_2],
        learning_centers_tree=True,
    )

    closest = learning_centers.get_closest(coordinates=(121.5, 130.2), k=1)

    assert learning_centers.members[closest[0]] == learning_center_2
