from june.demography import Person, Population
from june.time import Timer
from june.world import World
from june.groups import *
from june.policy import Policies

from camps.groups import LearningCenter, LearningCenters
from camps.activity import CampActivityManager

def make_dummy_world():
    pupil_shift_1 = Person.from_attributes(age=12, sex='f')
    pupil_shift_2 = Person.from_attributes(age=5, sex='m')
    pupil_shift_3 = Person.from_attributes(age=11, sex='f')
    learning_center = LearningCenter()
    household = Household()
    household.add(person=pupil_shift_1)
    household.add(person=pupil_shift_2)
    household.add(person=pupil_shift_3)
    learning_center.add(person=pupil_shift_1, shift=0)
    learning_center.add(person=pupil_shift_2, shift=1)
    learning_center.add(person=pupil_shift_3, shift=2)
    world = World()
    world.learning_centers = LearningCenters([learning_center])
    world.households = Households([household])
    world.people = Population([pupil_shift_1, pupil_shift_2, pupil_shift_3])
    for person in world.people.members:
        person.busy = False
    learning_center.clear()
    household.clear()
    return pupil_shift_1, pupil_shift_2, pupil_shift_3, learning_center, household, world

def make_dummy_activity_manager(world):
    timer = Timer(
            total_days=10,
            weekday_step_duration=[8,8,8],
            weekend_step_duration=[8,8,8],
            weekday_activities=[['primary_activity', 'residence'],
                ['primary_activity', 'residence']],
            weekend_activities=[['primary_activity', 'residence'],
                ['primary_activity', 'residence']]
            )
    activity_manager = CampActivityManager(
            world=world,
            policies=Policies.from_file(),
            timer=timer,
            all_activities=['primary_activity', 'residence'],
            activity_to_groups={'primary_activity': ['learning_centers'],
                'residence': ['households']}
            )
    return activity_manager


def test__activate_next_shift():

    pupil_shift_1, pupil_shift_2, pupil_shift_3, learning_center, household, world = make_dummy_world()
    activity_manager = make_dummy_activity_manager(world)
    assert learning_center.active_shift == 0
    activity_manager.activate_next_shift()
    assert learning_center.active_shift == 1
    activity_manager.activate_next_shift()
    assert learning_center.active_shift == 2
    activity_manager.activate_next_shift()
    assert learning_center.active_shift == 0

def test__shift_manager_moving_people():
    pupil_shift_1, pupil_shift_2, pupil_shift_3, learning_center, household, world = make_dummy_world()
    activity_manager = make_dummy_activity_manager(world)
    assert pupil_shift_1.id in learning_center.ids_per_shift[0]
    assert pupil_shift_2.id in learning_center.ids_per_shift[1]
    assert pupil_shift_3.id in learning_center.ids_per_shift[2]
    activity_manager.do_timestep()

    assert pupil_shift_1  in learning_center.people
    assert pupil_shift_2 not in learning_center.people
    assert pupil_shift_3 not in learning_center.people

    learning_center.clear()
    for person in world.people.members:
        person.busy = False
    activity_manager.do_timestep()

    assert pupil_shift_1 not in learning_center.people
    assert pupil_shift_2 in learning_center.people
    assert pupil_shift_3 not in learning_center.people

    learning_center.clear()
    for person in world.people.members:
        person.busy = False
    activity_manager.do_timestep()
    assert pupil_shift_1 not in learning_center.people
    assert pupil_shift_2 not in learning_center.people
    assert pupil_shift_3 in learning_center.people

    learning_center.clear()
    for person in world.people.members:
        person.busy = False
    activity_manager.do_timestep()
    assert pupil_shift_1 in learning_center.people
    assert pupil_shift_2 not in learning_center.people
    assert pupil_shift_3 not in learning_center.people


