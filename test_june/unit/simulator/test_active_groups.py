import pytest
from june.infection.health_index import HealthIndexGenerator

@pytest.fixture(name='health_index')
def create_health_index():
    def dummy_health_index(age, sex):
        return [0.1, 0.3, 0.5, 0.7, 0.9]
    return dummy_health_index 

def test__hospitalise_the_sick(simulator, health_index):
    dummy_person = simulator.world.people.members[0]
    simulator.infection.infect_person_at_time(dummy_person, health_index, simulator.timer.now)
    dummy_person.health_information.infection.symptoms.severity = 0.75
    simulator.hospitalise_the_sick(dummy_person)
    assert dummy_person.in_hospital is not None


def test__right_group_hierarchy(simulator):
    permanent_group_hierarchy = simulator.permanent_group_hierarchy.copy()
    permanent_group_hierarchy.reverse()
    active_groups = permanent_group_hierarchy.copy()
    ordered_active_groups = simulator.apply_group_hierarchy(active_groups)
    assert ordered_active_groups == simulator.permanent_group_hierarchy


def test__right_group_hierarchy_random_groups(simulator):
    # Add some random groups
    permanent_group_hierarchy = simulator.permanent_group_hierarchy.copy()
    permanent_group_hierarchy.reverse()
    active_groups = permanent_group_hierarchy.copy()
    #active_groups += ["pubs"]
    ordered_active_groups = simulator.apply_group_hierarchy(active_groups)
    true_ordered_active_groups = [
        group
        for group in simulator.permanent_group_hierarchy
        if group not in ["carehomes", "households"]
    ]
    #true_ordered_active_groups.append("pubs")
    true_ordered_active_groups += ["carehomes", "households"]
    assert ordered_active_groups == true_ordered_active_groups


def test__right_group_hierarchy_in_box(simulator_box):
    ordered_active_groups = simulator_box.apply_group_hierarchy(["boxes"])

    assert ordered_active_groups == ["boxes"]


def test__everyone_is_freed(simulator):
    simulator.set_active_group_to_people(["carehomes", "households"])
    simulator.set_allpeople_free()
    for person in simulator.world.people.members:
        assert person.active_group == None
    simulator.set_allpeople_free()


def test__everyone_is_in_household(simulator):
    simulator.set_active_group_to_people(["carehomes", "households"])
    for person in simulator.world.people.members:
        assert person.active_group in ["carehome", "household"]
    simulator.set_allpeople_free()


def test__households_carehomes_are_exclusive(simulator):
    for person in simulator.world.people.members:
        if person.household is not None:
            assert person.carehome is None
        else:
            assert person.carehome is not None
            assert person.household is None


def test__everyone_is_in_school_household(simulator):
    simulator.set_active_group_to_people(["schools", "carehomes", "households"])
    for person in simulator.world.people.members:
        if person.school is not None:
            should_be_active = "school"
        elif person.carehome is not None:
            should_be_active = "carehome"
        elif person.household is not None:
            should_be_active = "household"
        assert person.active_group == should_be_active
    simulator.set_allpeople_free()


def test__everyone_is_active_somewhere(simulator):
    simulator.set_active_group_to_people(["schools", "carehomes", "households"])
    for person in simulator.world.people.members:
        assert person.active_group is not None
    simulator.set_allpeople_free()


def find_random_in_school(simulator):
    for school in simulator.world.schools.members:
        for grouping in school.subgroups:
            for person in grouping._people:
                selected_person = person
                break
    return selected_person


def test__follow_a_pupil(simulator):
    selected_person = find_random_in_school(simulator)
    simulator.set_allpeople_free()
    simulator.timer.reset()
    for day in simulator.timer:
        active_groups = simulator.timer.active_groups()
        simulator.set_active_group_to_people(active_groups)
        should_be_active = "school" if "schools" in active_groups else "household"
        assert selected_person.active_group == should_be_active
        simulator.set_allpeople_free()
        assert selected_person.active_group == None
        if day > 10:
            break
    simulator.set_allpeople_free()
    simulator.timer.reset()


def test__sick_gets_to_hospital_recovers_and_leaves(simulator, health_index):
    # sick goes to hospital
    dummy_person = simulator.world.people.members[0]
    simulator.infection.infect_person_at_time(dummy_person, health_index, simulator.timer.now)
    dummy_person.health_information.infection.symptoms.severity = 0.75
    simulator.update_health_status(simulator.timer.now, 0)
    assert dummy_person.in_hospital is not None
    simulator.set_active_group_to_people(["schools", "hospitals", "households"])
    assert dummy_person.active_group == "hospital"
    simulator.set_allpeople_free()
    dummy_person.health_information.recovered = True
    simulator.update_health_status(simulator.timer.now, 0)
    assert dummy_person.in_hospital is None
    simulator.set_active_group_to_people(["schools", "hospitals", "households"])
    assert dummy_person.active_group != "hospital"
    simulator.set_allpeople_free()


@pytest.mark.parametrize("severity", [0.2, 0.4])
def test__must_stay_at_home_kid_drags_parents(simulator, health_index, severity):
    # infect all kids in one school
    for school in simulator.world.schools.members:
        if len(school.people) > 10:
            break

    for dummy_person in list(school.people)[:10]:
        simulator.infection.infect_person_at_time(dummy_person, health_index, simulator.timer.now)
        dummy_person.health_information.infection.symptoms.severity = severity
        simulator.set_active_group_to_people(["hospitals", "companies", "households"])
        assert dummy_person.active_group == "household"
        assert dummy_person.health_information.tag in (
            "influenza-like illness",
            "pneumonia",
        )

        if dummy_person.age <= 14:
            parent_at_home = 0
            parents = [
                person
                for person in dummy_person.household.people
                if person
                not in list(
                    dummy_person.household.subgroups[
                        dummy_person.household.GroupType.kids
                    ].people
                )
            ]
            for person in parents:
                if person.active_group == "household":
                    parent_at_home += 1
            assert parent_at_home > 0
    simulator.set_allpeople_free()


def test__bury_the_dead(simulator, health_index):
    # TODO : bring them back to life if you want to keep using the simulator clean
    # in the (near?) future we will be able to create a test simulator
    # that is quick, and therefore doesn't need to be a fixture
    dummy_person = simulator.world.people.members[0]

    simulator.infection.infect_person_at_time(dummy_person, health_index, simulator.timer.now)
    dummy_person.health_information.infection.symptoms.severity = 0.99 

    assert dummy_person.household is not None
    assert dummy_person in dummy_person.household.people
    simulator.bury_the_dead(dummy_person)
    assert dummy_person not in dummy_person.household.people
    simulator.set_allpeople_free()
    simulator.set_active_group_to_people(["hospitals", "households"])
    assert dummy_person.active_group is None
    simulator.set_allpeople_free()

