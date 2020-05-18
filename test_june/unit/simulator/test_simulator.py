import pytest
import random

from june.geography import Geography
from june.demography import Demography
from june.world import World
from june.interaction import DefaultInteraction
from june.infection import Infection
from june.infection.symptoms import Symptom_Tags, SymptomsConstant
from june.infection.transmission import TransmissionConstant
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
from june.simulator import Simulator


@pytest.fixture(name="sim", scope="module")
def create_simulator():

    geography = Geography.from_file({"msoa": ["E00088544", "E02002560", "E02002559"]})
    geography.hospitals = Hospitals.for_geography(geography)
    geography.cemeteries = Cemeteries()
    geography.care_homes = CareHomes.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    demography = Demography.for_geography(geography)
    world = World(geography, demography, include_households=True)
    selector = InfectionSelector(transmission_type="Constant",
                                 symptoms_type="Constant")
    selector.recovery_rate=0.05
    selector.transmission_probability=0.7
    infection   = Infection(transmission, symptoms)
    interaction = DefaultInteraction.from_file()
    interaction.selector = selector
    return Simulator.from_file(world, interaction, infection,)


@pytest.fixture(name="health_index")
def create_health_index():
    def dummy_health_index(age, sex):
        return [0.1, 0.3, 0.5, 0.7, 0.9]

    return dummy_health_index


def test__everyone_has_an_activity(sim):
    for person in sim.world.people.members:
        assert person.subgroups.count(None) != len(person.subgroups)


def test__apply_activity_hierarchy(sim):
    unordered_activities = random.sample(
        sim.permanent_activity_hierarchy, len(sim.permanent_activity_hierarchy)
    )
    ordered_activities = sim.apply_activity_hierarchy(unordered_activities)
    assert ordered_activities == sim.permanent_activity_hierarchy


def test__activities_to_groups(sim):
    activities = ["hospital", "primary_activity", "residence"]
    groups = sim.activities_to_groups(activities)

    assert groups == ["hospitals", "schools", "companies", "households", "care_homes"]


def test__clear_world(sim):
    sim.clear_world()
    for group_name in sim.activities_to_groups(sim.all_activities):
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


def test__move_people_to_primary_activity(sim):

    sim.move_people_to_active_subgroups(["primary_activity", "residence"])
    for person in sim.world.people.members:
        if person.primary_activity is not None:
            assert person in person.primary_activity.people
    sim.clear_world()


def test__kid_at_home_is_supervised(sim, health_index):

    kids_at_school = []
    for person in sim.world.people.members:
        if person.primary_activity is not None and person.age < sim.min_age_home_alone:
            kids_at_school.append(person)

    for kid in kids_at_school:
        sim.infection.infect_person_at_time(kid, health_index, 0.0)
        kid.health_information.infection.symptoms.severity = 0.4
        assert kid.health_information.must_stay_at_home

    sim.move_people_to_active_subgroups(["primary_activity", "residence"])

    for kid in kids_at_school:
        assert kid in kid.residence.people
        guardians_at_home = [
            person for person in kid.residence.group.people if person.age >= 18
        ]
        assert len(guardians_at_home) != 0

    sim.clear_world()


def test__hospitalise_the_sick(sim, health_index):
    hospital_severity = 0.6
    dummy_person = sim.world.people.members[0]
    sim.infection.infect_person_at_time(dummy_person, health_index, 0.0)
    dummy_person.health_information.infection.symptoms.severity = hospital_severity 
    assert dummy_person.health_information.should_be_in_hospital
    sim.update_health_status(0., 0.)
    assert dummy_person.hospital is not None
    sim.move_people_to_active_subgroups(["hospital", "residence"])
    assert dummy_person in dummy_person.hospital.people
    sim.clear_world()


def test__move_people_from_hospital_to_icu(sim):
    icu_severity = 0.8
    dummy_person = sim.world.people.members[0]
    dummy_person.health_information.infection.symptoms.severity = icu_severity 
    assert dummy_person.health_information.tag == 'intensive care'
    sim.hospitalise_the_sick(dummy_person, 'hospitalised')
    hospital = dummy_person.hospital.group
    sim.move_people_to_active_subgroups(["hospital", "residence"])
    assert dummy_person in hospital[hospital.SubgroupType.icu_patients]
    sim.clear_world()

def test__move_people_from_icu_to_hospital(sim):
    hospital_severity = 0.6
    dummy_person = sim.world.people.members[0]
    dummy_person.health_information.infection.symptoms.severity = hospital_severity 
    assert dummy_person.health_information.tag == 'hospitalised'
    sim.hospitalise_the_sick(dummy_person, 'intensive care')
    hospital = dummy_person.hospital.group
    sim.move_people_to_active_subgroups(["hospital", "residence"])
    assert dummy_person in hospital[hospital.SubgroupType.patients]
    sim.clear_world()


def test__bury_the_dead(sim):
    dummy_person = sim.world.people.members[0]
    sim.bury_the_dead(dummy_person, 0.)

    assert dummy_person in sim.world.cemeteries.members[0].people
    assert dummy_person.health_information.dead
    assert dummy_person.health_information.infection is None
