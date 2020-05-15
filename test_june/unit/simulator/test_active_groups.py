import pytest
from june.infection.health_index import HealthIndexGenerator
from june.demography import Demography
from june.groups import Hospitals, Schools, Companies, CareHomes, Cemeteries
from june import World
from june.simulator import Simulator

@pytest.fixture(name="world_bonito", scope='module')
def create_world(geography):
    demography = Demography.for_geography(geography)
    geography.hospitals = Hospitals.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.carehomes = CareHomes.for_geography(geography)
    geography.cemeteries = Cemeteries()
    geography.companies = Companies.for_geography(geography)
    world_bonito = World(geography, demography, include_households=True)
    return world_bonito


@pytest.fixture(name="simulator_bonito", scope='module')
def create_simulator_bonito(world_bonito, interaction, infection_healthy):
    return Simulator.from_file(world_bonito, interaction, infection_healthy)



@pytest.fixture(name="health_index")
def create_health_index():
    def dummy_health_index(age, sex):
        return [0.1, 0.3, 0.5, 0.7, 0.9]

    return dummy_health_index

def test__everyone_is_in_school_household(simulator_bonito):
    simulator_bonito.set_allpeople_free()
    simulator_bonito.set_active_group_to_people(["schools", "carehomes", "households"])
    for person in simulator_bonito.world.people.members:
        if person.school is not None:
            should_be_active = "school"
        elif person.carehome is not None:
            should_be_active = "carehome"
        elif person.household is not None:
            should_be_active = "household"
        assert person.active_group.spec == should_be_active
    simulator_bonito.set_allpeople_free()


def test__everyone_is_in_household(simulator_bonito):
    simulator_bonito.set_allpeople_free()
    simulator_bonito.set_active_group_to_people(["carehomes", "households"])
    for person in simulator_bonito.world.people.members:
        assert person in person.subgroups[person.GroupType.residence].people
        assert person.active_group.spec in ["carehome", "household"]
    simulator_bonito.set_allpeople_free()

def test__everyone_is_freed(simulator_bonito):
    simulator_bonito.set_active_group_to_people(["carehomes", "households"])
    simulator_bonito.set_allpeople_free()
    for person in simulator_bonito.world.people.members:
        assert person.active_group == None




def test__right_group_hierarchy(simulator_bonito):
    permanent_group_hierarchy = simulator_bonito.permanent_group_hierarchy.copy()
    permanent_group_hierarchy.reverse()
    active_groups = permanent_group_hierarchy.copy()
    ordered_active_groups = simulator_bonito.apply_group_hierarchy(active_groups)
    assert ordered_active_groups == simulator_bonito.permanent_group_hierarchy


def test__right_group_hierarchy_random_groups(simulator_bonito):
    # Add some random groups
    permanent_group_hierarchy = simulator_bonito.permanent_group_hierarchy.copy()
    permanent_group_hierarchy.reverse()
    active_groups = permanent_group_hierarchy.copy()
    # active_groups += ["pubs"]
    ordered_active_groups = simulator_bonito.apply_group_hierarchy(active_groups)
    true_ordered_active_groups = [
        group
        for group in simulator_bonito.permanent_group_hierarchy
        if group not in ["carehomes", "households"]
    ]
    # true_ordered_active_groups.append("pubs")
    true_ordered_active_groups += ["carehomes", "households"]
    assert ordered_active_groups == true_ordered_active_groups


def test__right_group_hierarchy_in_box(simulator_box):
    ordered_active_groups = simulator_box.apply_group_hierarchy(["boxes"])

    assert ordered_active_groups == ["boxes"]



def test__households_carehomes_are_exclusive(simulator_bonito):
    for person in simulator_bonito.world.people.members:
        if person.household is not None:
            assert person.carehome is None
        else:
            assert person.carehome is not None
            assert person.household is None


def test__everyone_is_active_somewhere(simulator_bonito):
    simulator_bonito.set_active_group_to_people(["schools", "carehomes", "households"])
    for person in simulator_bonito.world.people.members:
        assert person.active_group.spec is not None
    simulator_bonito.set_allpeople_free()


def find_random_in_school(simulator_bonito):
    for school in simulator_bonito.world.schools.members:
        for grouping in school.subgroups:
            for person in grouping._people:
                selected_person = person
                break
    return selected_person


def test__follow_a_pupil(simulator_bonito):
    selected_person = find_random_in_school(simulator_bonito)
    simulator_bonito.set_allpeople_free()
    simulator_bonito.timer.reset()
    for day in simulator_bonito.timer:
        active_groups = simulator_bonito.timer.active_groups()
        simulator_bonito.set_active_group_to_people(active_groups)
        should_be_active = "school" if "schools" in active_groups else "household"
        assert selected_person.active_group.spec == should_be_active
        simulator_bonito.set_allpeople_free()
        assert selected_person.active_group == None
        if day > 10:
            break
    simulator_bonito.set_allpeople_free()
    simulator_bonito.timer.reset()

def test__hospitalise_the_sick(simulator_bonito, health_index):
    dummy_person = simulator_bonito.world.people.members[0]
    simulator_bonito.infection.infect_person_at_time(dummy_person, health_index, simulator_bonito.timer.now)
    dummy_person.health_information.infection.symptoms.severity = 0.75
    simulator_bonito.hospitalise_the_sick(dummy_person)
    assert dummy_person.in_hospital is not None



def test__sick_gets_to_hospital_recovers_and_leaves(simulator_bonito, health_index):
    # sick goes to hospital
    dummy_person = simulator_bonito.world.people.members[0]
    simulator_bonito.infection.infect_person_at_time(
        dummy_person, health_index, simulator_bonito.timer.now
    )
    dummy_person.health_information.infection.symptoms.severity = 0.75
    simulator_bonito.update_health_status(simulator_bonito.timer.now, 0)
    assert dummy_person.in_hospital is not None
    simulator_bonito.set_active_group_to_people(["schools", "hospitals", "households"])
    assert dummy_person.active_group.spec == "hospital"
    simulator_bonito.set_allpeople_free()
    dummy_person.health_information.recovered = True
    simulator_bonito.update_health_status(simulator_bonito.timer.now, 0)
    assert dummy_person.in_hospital is None
    simulator_bonito.set_active_group_to_people(["schools", "hospitals", "households"])
    assert dummy_person.active_group.spec != "hospital"
    simulator_bonito.set_allpeople_free()


@pytest.mark.parametrize("severity", [0.2, 0.4])
def test__must_stay_at_home_kid_drags_parents(simulator_bonito, health_index, severity):
    # infect all kids in one school
    for school in simulator_bonito.world.schools.members:
        if len(school.people) > 10:
            break

    for dummy_person in list(school.people)[:10]:
        simulator_bonito.infection.infect_person_at_time(
            dummy_person, health_index, simulator_bonito.timer.now
        )
        dummy_person.health_information.infection.symptoms.severity = severity
        assert dummy_person.health_information.tag in (
            "influenza-like illness",
            "pneumonia",
        )
        assert dummy_person.health_information.must_stay_at_home

        simulator_bonito.set_active_group_to_people(["hospitals", "companies", "households"])
        assert dummy_person.active_group.spec == "household"

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
                if person.active_group.spec == "household":
                    parent_at_home += 1
            assert parent_at_home > 0
    simulator_bonito.set_allpeople_free()


def test__bury_the_dead(simulator_bonito, health_index):
    # TODO : bring them back to life if you want to keep using the simulator_bonito clean
    # in the (near?) future we will be able to create a test simulator_bonito
    # that is quick, and therefore doesn't need to be a fixture
    dummy_person = simulator_bonito.world.people.members[10]

    simulator_bonito.infection.infect_person_at_time(
        dummy_person, health_index, simulator_bonito.timer.now
    )
    dummy_person.health_information.infection.symptoms.severity = 0.99

    assert dummy_person.household is not None
    assert dummy_person in dummy_person.household.people
    simulator_bonito.bury_the_dead(dummy_person, 0)
    assert dummy_person not in dummy_person.household.people
    simulator_bonito.set_allpeople_free()
    simulator_bonito.set_active_group_to_people(["hospitals", "households"])
    assert dummy_person.active_group is None
    simulator_bonito.set_allpeople_free()

def test__bury_the_dead_children(simulator_bonito, health_index):
    # find kid
    for person in simulator_bonito.world.people.members:
        if person.age > 5 and person.age < 10:
            dummy_person = person
            break
    simulator_bonito.infection.infect_person_at_time(dummy_person, health_index, simulator_bonito.timer.now)
    dummy_person.health_information.infection.symptoms.severity = 0.99 
    assert dummy_person.household is not None
    assert dummy_person.school is not None
    assert dummy_person in dummy_person.household.people
    assert dummy_person in dummy_person.school.people
    simulator_bonito.bury_the_dead(dummy_person, 0)
    assert dummy_person not in dummy_person.household.people
    simulator_bonito.set_allpeople_free()
    simulator_bonito.set_active_group_to_people(["hospitals", "schools", "households"])
    assert dummy_person.active_group is None
    simulator_bonito.set_allpeople_free()

