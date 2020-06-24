import random

import pytest

from june import paths
from june.demography import Demography
from june.demography.geography import Geography
from june.groups import Hospitals, Schools, Companies, CareHomes, Cemeteries, Universities
from june.groups.leisure import leisure, Cinemas, Pubs, Groceries
from june.infection import InfectionSelector, SymptomTag
from june.interaction import ContactAveraging
from june.simulator import Simulator
from june.world import generate_world_from_geography

constant_config = paths.configs_path / "defaults/infection/InfectionConstant.yaml"
test_config = paths.configs_path / "tests/test_simulator.yaml"


@pytest.fixture(name="sim", scope="module")
def create_simulator():
    geography = Geography.from_file(
        {
            "super_area": [
                "E02003282",
                "E02001720",
                "E00088544",
                "E02002560",
                "E02002559",
                "E02004314",
            ]
        }
    )
    geography.hospitals = Hospitals.for_geography(geography)
    geography.cemeteries = Cemeteries()
    geography.care_homes = CareHomes.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.universities = Universities.for_super_areas(geography.super_areas)
    geography.companies = Companies.for_geography(geography)
    world = generate_world_from_geography(
        geography=geography, include_commute=True, include_households=True
    )
    world.cinemas = Cinemas.for_geography(geography)
    world.pubs = Pubs.for_geography(geography)
    world.groceries = Groceries.for_super_areas(
        geography.super_areas, venues_per_capita=1 / 500
    )
    leisure_instance = leisure.generate_leisure_for_config(
        world=world, config_filename=test_config
    )
    selector = InfectionSelector.from_file(config_filename=constant_config)
    selector.recovery_rate = 0.05
    selector.transmission_probability = 0.7
    interaction = ContactAveraging.from_file()
    interaction.selector = selector
    sim = Simulator.from_file(
        world,
        interaction,
        selector,
        config_filename=test_config,
        leisure=leisure_instance,
    )
    return sim


@pytest.fixture(name="health_index")
def create_health_index():
    def dummy_health_index(age, sex):
        return [0.1, 0.3, 0.5, 0.7, 0.9]

    return dummy_health_index


def test__everyone_has_an_activity(sim):
    for person in sim.world.people.members:
        assert person.subgroups.iter().count(None) != len(person.subgroups)


def test__apply_activity_hierarchy(sim):
    unordered_activities = random.sample(
        sim.activity_hierarchy, len(sim.activity_hierarchy)
    )
    ordered_activities = sim.apply_activity_hierarchy(unordered_activities)
    assert ordered_activities == sim.activity_hierarchy


def test__activities_to_groups(sim):
    activities = ["hospital", "commute", "primary_activity", "leisure", "residence"]
    groups = sim.activities_to_groups(activities)

    assert groups == [
        "hospitals",
        "commuteunits",
        "commutecityunits",
        "schools",
        "companies",
        "universities",
        "pubs",
        "cinemas",
        "groceries",
        "household_visits",
        "care_home_visits",
        "households",
        "care_homes",
    ]


def test__clear_world(sim):
    sim.clear_world()
    for group_name in sim.activities_to_groups(sim.all_activities):
        if group_name in ["household_visits", "care_home_visits"]:
            continue
        grouptype = getattr(sim.world, group_name)
        for group in grouptype.members:
            for subgroup in group.subgroups:
                assert len(subgroup.people) == 0

    for person in sim.world.people.members:
        assert person.busy == False


def test__get_subgroup_active(sim):
    active_subgroup = sim.get_subgroup_active(
        ["residence"], sim.world.people.members[0]
    )
    assert active_subgroup.group.spec in ("carehome", "household")


def test__move_people_to_residence(sim):
    sim.move_people_to_active_subgroups(["residence"])
    for person in sim.world.people.members:
        assert person in person.residence.people
    sim.clear_world()


def test__move_people_to_leisure(sim):
    sim.clear_world()
    sim.move_people_to_active_subgroups(["leisure", "residence"])
    n_leisure = 0
    n_cinemas = 0
    n_pubs = 0
    n_groceries = 0
    for person in sim.world.people.members:
        if person.leisure is not None:
            n_leisure += 1
            if person.leisure.group.spec == "care_home":
                assert person.leisure.subgroup_type == 2  # visitors
            elif person.leisure.group.spec == "cinema":
                n_cinemas += 1
            elif person.leisure.group.spec == "pub":
                n_pubs += 1
            elif person.leisure.group.spec == "grocery":
                n_groceries += 1
            # print(f'There are {len(person.leisure.people)} in this group')
            assert person in person.leisure.people
    assert n_leisure > 0
    assert n_cinemas > 0
    assert n_pubs > 0
    assert n_groceries > 0
    sim.clear_world()


def test__move_people_to_primary_activity(sim):
    sim.move_people_to_active_subgroups(["primary_activity", "residence"])
    for person in sim.world.people.members:
        if person.primary_activity is not None:
            assert person in person.primary_activity.people
    sim.clear_world()


def test__move_people_to_commute(sim):
    sim.distribute_commuters()
    sim.move_people_to_active_subgroups(["commute", "residence"])
    n_commuters = 0
    for person in sim.world.people.members:
        if person.commute is not None:
            n_commuters += 1
            assert person in person.commute.people
    assert n_commuters > 0
    sim.clear_world()


def test__kid_at_home_is_supervised(sim, health_index):
    kids_at_school = []
    for person in sim.world.people.members:
        if person.primary_activity is not None and person.age < sim.min_age_home_alone:
            kids_at_school.append(person)

    for kid in kids_at_school:
        sim.selector.infect_person_at_time(kid, 0.0)
        kid.health_information.infection.symptoms.tag = SymptomTag.influenza
        assert kid.health_information.must_stay_at_home

    sim.move_people_to_active_subgroups(["primary_activity", "residence"])

    for kid in kids_at_school:
        assert kid in kid.residence.people
        guardians_at_home = [
            person for person in kid.residence.group.people if person.age >= 18
        ]
        assert len(guardians_at_home) != 0

    sim.clear_world()


def test__hospitalise_the_sick(sim):
    dummy_person = sim.world.people.members[0]
    sim.selector.infect_person_at_time(dummy_person, 0.0)
    dummy_person.health_information.infection.symptoms.tag = SymptomTag.hospitalised
    assert dummy_person.health_information.should_be_in_hospital
    sim.update_health_status(0.0, 0.0)
    assert dummy_person.hospital is not None
    sim.move_people_to_active_subgroups(["hospital", "residence"])
    assert dummy_person in dummy_person.hospital.people
    sim.clear_world()


def test__move_people_from_hospital_to_icu(sim):
    dummy_person = sim.world.people.members[0]
    dummy_person.health_information.infection.symptoms.tag = SymptomTag.intensive_care
    sim.hospitalise_the_sick(dummy_person, "hospitalised")
    hospital = dummy_person.hospital.group
    sim.move_people_to_active_subgroups(["hospital", "residence"])
    assert dummy_person in hospital[hospital.SubgroupType.icu_patients]
    sim.clear_world()


def test__move_people_from_icu_to_hospital(sim):
    dummy_person = sim.world.people.members[0]
    dummy_person.health_information.infection.symptoms.tag = SymptomTag.hospitalised
    sim.hospitalise_the_sick(dummy_person, "intensive care")
    hospital = dummy_person.hospital.group
    sim.move_people_to_active_subgroups(["hospital", "residence"])
    assert dummy_person in hospital[hospital.SubgroupType.patients]
    sim.clear_world()


def test__bury_the_dead(sim):
    dummy_person = sim.world.people.members[0]
    sim.bury_the_dead(dummy_person, 0.0)

    assert dummy_person in sim.world.cemeteries.members[0].people
    assert dummy_person.health_information.dead
    assert dummy_person.health_information.infection is None
