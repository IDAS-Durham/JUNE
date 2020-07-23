import random
from datetime import datetime
import pytest

from june import paths
from june.demography import Person, Population
from june.demography.geography import Geography, Area, SuperArea, Areas, SuperAreas
from june.world import World
from june.groups import Hospitals, Schools, Companies, CareHomes, Universities
from june.groups.leisure import leisure, Cinemas, Pubs, Groceries
from june.infection import InfectionSelector, SymptomTag
from june.interaction import ContactAveraging
from june.policy import (
    Policies,
    Hospitalisation,
    MedicalCarePolicies,
    SevereSymptomsStayHome,
    IndividualPolicies,
)
from june.groups import Hospital, School, Company, Household, University, CareHome
from june.groups import (
    Hospitals,
    Schools,
    Companies,
    Households,
    Universities,
    Cemeteries,
)
from june.groups.leisure import leisure, Cinemas, Pubs, Cinema, Pub, Grocery, Groceries
from june.simulator import Simulator, activity_hierarchy
from june.world import generate_world_from_geography, generate_world_from_hdf5

constant_config = paths.configs_path / "defaults/infection/InfectionConstant.yaml"
test_config = paths.configs_path / "tests/test_simulator.yaml"


@pytest.fixture(name="selector", scope="module")
def make_selector():
    selector = InfectionSelector.from_file(config_filename=constant_config)
    selector.recovery_rate = 0.05
    selector.transmission_probability = 0.7
    return selector


@pytest.fixture(name="medical_policies")
def make_policies():
    policies = Policies([Hospitalisation()])
    return MedicalCarePolicies.get_active_policies(policies=policies, date=datetime(2020, 3, 1))


@pytest.fixture(name="sim", scope="module")
def create_simulator(selector):
    super_area = SuperArea(name="E02002559", coordinates=[1,1])
    area = Area(name="E00062207", super_area=super_area, coordinates=[1,1])
    areas = Areas([area])
    super_area.areas = areas
    super_areas = SuperAreas([super_area])
    company = Company(super_area=super_area, n_workers_max=100, sector="Q")
    school = School(
        coordinates=super_area.coordinates,
        n_pupils_max=100,
        age_min=4,
        age_max=10,
        sector="primary",
    )
    household = Household()
    household.area = super_area.areas[0]
    care_home = CareHome()
    hospital = Hospital(
        n_beds=40,
        n_icu_beds=5,
        super_area=super_area.name,
        coordinates=super_area.coordinates,
    )
    worker = Person.from_attributes(age=40)
    worker.area = super_area
    household.add(worker, subgroup_type=household.SubgroupType.adults)
    worker.sector = "Q"
    company.add(worker)

    pupil = Person.from_attributes(age=6)
    pupil.area = super_area
    household.add(pupil, subgroup_type=household.SubgroupType.kids)
    household.area = super_area
    school.add(pupil)


    world = World()
    world.areas = areas
    world.super_areas = super_areas
    world.schools = Schools([school])
    world.hospitals = Hospitals([hospital])
    world.households = Households([household])
    world.universities = Universities([])
    world.companies = Companies([company])
    world.care_homes = CareHomes([CareHome()])
    commuter = Person.from_attributes(sex='m', age=30)
    world.people = Population([worker, pupil, commuter])
    cinema = Cinema()
    cinema.coordinates = super_area.coordinates
    world.cinemas = Cinemas([cinema])
    pub = Pub()
    pub.coordinates = super_area.coordinates
    world.pubs = Pubs([pub])
    grocery = Grocery()
    grocery.coordinates = super_area.coordinates
    world.groceries = Groceries([grocery])
    leisure_instance = leisure.generate_leisure_for_world(
        world=world, list_of_leisure_groups=["pubs", "cinemas", "groceries"]
    )
    world.initialise_commuting()
    world.commutehubs[0].add(commuter)
    world.cemeteries = Cemeteries()
    leisure_instance.distribute_social_venues_to_households(world.households)
    interaction = ContactAveraging.from_file()
    interaction.selector = selector
    policies = Policies.from_file()
    sim = Simulator.from_file(
        world=world,
        interaction=interaction,
        config_filename=test_config,
        leisure=leisure_instance,
        policies=policies,
    )
    sim.activity_manager.leisure.generate_leisure_probabilities_for_timestep(3, False)
    return sim

#def create_simulator(selector):
#    geography = Geography.from_file(
#        {
#            "super_area": [
#                "E02003282",
#                "E02001720",
#                "E00088544",
#                "E02002560",
#                "E02002559",
#                "E02004314",
#            ]
#        }
#    )
#    geography.hospitals = Hospitals.for_geography(geography)
#    geography.care_homes = CareHomes.for_geography(geography)
#    geography.schools = Schools.for_geography(geography)
#    geography.universities = Universities.for_super_areas(geography.super_areas)
#    geography.companies = Companies.for_geography(geography)
#    world = generate_world_from_geography(
#        geography=geography, include_commute=True, include_households=True
#    )
#    world.to_hdf5("simulator_tests.hdf5")
#    world = generate_world_from_hdf5("simulator_tests.hdf5")
#    world.cinemas = Cinemas.for_areas(world.areas)
#    world.pubs = Pubs.for_areas(world.areas)
#    world.groceries = Groceries.for_geography(geography)
#    leisure_instance = leisure.generate_leisure_for_config(
#        world=world, config_filename=test_config
#    )
#    leisure_instance.distribute_social_venues_to_households(world.households)
#    interaction = ContactAveraging.from_file()
#    interaction.selector = selector
#    policies = Policies.from_file()
#    sim = Simulator.from_file(
#        world=world,
#        interaction=interaction,
#        config_filename=test_config,
#        leisure=leisure_instance,
#        policies=policies,
#    )
#    sim.activity_manager.leisure.generate_leisure_probabilities_for_timestep(3, False)
#    return sim


@pytest.fixture(name="health_index")
def create_health_index():
    def dummy_health_index(age, sex):
        return [0.1, 0.3, 0.5, 0.7, 0.9]

    return dummy_health_index


def test__everyone_has_an_activity(sim: Simulator):
    for person in sim.world.people.members:
        assert person.subgroups.iter().count(None) != len(person.subgroups)


def test__apply_activity_hierarchy(sim: Simulator):
    unordered_activities = random.sample(activity_hierarchy, len(activity_hierarchy))
    ordered_activities = sim.activity_manager.apply_activity_hierarchy(
        unordered_activities
    )
    assert ordered_activities == activity_hierarchy


def test__activities_to_groups(sim: Simulator):
    activities = [
        "medical_facility",
        "commute",
        "primary_activity",
        "leisure",
        "residence",
    ]
    groups = sim.activity_manager.activities_to_groups(activities)

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


def test__clear_world(sim: Simulator):
    sim.clear_world()
    for group_name in sim.activity_manager.activities_to_groups(
        sim.activity_manager.all_activities
    ):
        if group_name in ["household_visits", "care_home_visits"]:
            continue
        grouptype = getattr(sim.world, group_name)
        print(group_name)
        for group in grouptype.members:
            for subgroup in group.subgroups:
                assert len(subgroup.people) == 0

    for person in sim.world.people.members:
        assert person.busy == False


def test__move_to_active_subgroup(sim: Simulator):
    sim.activity_manager.move_to_active_subgroup(
        ["residence"], sim.world.people.members[0]
    )
    assert sim.world.people.members[0].residence.group.spec in ("carehome", "household")


def test__move_people_to_residence(sim: Simulator):
    sim.activity_manager.move_people_to_active_subgroups(["residence"])
    for person in sim.world.people.members:
        assert person in person.residence.people
    sim.clear_world()


def test__move_people_to_leisure(sim: Simulator):
    n_leisure = 0
    n_cinemas = 0
    n_pubs = 0
    n_groceries = 0
    repetitions = 500
    for _ in range(repetitions):
        sim.clear_world()
        sim.activity_manager.move_people_to_active_subgroups(["leisure", "residence"])
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


def test__move_people_to_primary_activity(sim: Simulator):
    sim.activity_manager.move_people_to_active_subgroups(
        ["primary_activity", "residence"]
    )
    for person in sim.world.people.members:
        if person.primary_activity is not None:
            assert person in person.primary_activity.people
    sim.clear_world()


def test__move_people_to_commute(sim: Simulator):
    sim.activity_manager.distribute_commuters()
    sim.activity_manager.move_people_to_active_subgroups(["commute", "residence"])
    n_commuters = 0
    for person in sim.world.people.members:
        if person.commute is not None:
            n_commuters += 1
            assert person in person.commute.people
    assert n_commuters > 0
    sim.clear_world()


def test__kid_at_home_is_supervised(sim: Simulator, selector):
    kids_at_school = []
    for person in sim.world.people.members:
        if person.primary_activity is not None and person.age < 15:
            kids_at_school.append(person)

    for kid in kids_at_school:

        selector.infect_person_at_time(kid, 0.0)
        kid.health_information.infection.symptoms.tag = getattr(SymptomTag, "severe")
        kid.health_information.infection.symptoms.tag = SymptomTag.severe
    sim.activity_manager.move_people_to_active_subgroups(
        ["primary_activity", "residence"]
    )

    for kid in kids_at_school:
        assert kid in kid.residence.people
        guardians_at_home = [
            person for person in kid.residence.group.people if person.age >= 18
        ]
        assert len(guardians_at_home) != 0

    sim.clear_world()


def test__hospitalise_the_sick(sim: Simulator, selector, medical_policies):
    dummy_person = sim.world.people.members[0]
    selector.infect_person_at_time(dummy_person, 0.0)
    dummy_person.health_information.infection.symptoms.tag = SymptomTag.hospitalised
    assert dummy_person.health_information.should_be_in_hospital
    medical_policies.apply(
        person=dummy_person, medical_facilities=[sim.world.hospitals[0]]
    )
    sim.update_health_status(0.0, 0.0)
    assert dummy_person.hospital is not None
    sim.activity_manager.move_people_to_active_subgroups(["hospital", "residence"])
    assert dummy_person in dummy_person.hospital.people
    sim.clear_world()


def test__move_people_from_hospital_to_icu(sim: Simulator, medical_policies):
    dummy_person = sim.world.people.members[0]
    dummy_person.health_information.infection.symptoms.tag = SymptomTag.intensive_care
    # sim.hospitalise_the_sick(dummy_person, "hospitalised")
    medical_policies.apply(person=dummy_person, medical_facilities=[hospital])
    hospital = dummy_person.hospital.group
    sim.activity_manager.move_people_to_active_subgroups(["hospital", "residence"])
    assert dummy_person in hospital[hospital.SubgroupType.icu_patients]
    sim.clear_world()


def test__move_people_from_icu_to_hospital(sim: Simulator, medical_policies):
    dummy_person = sim.world.people.members[0]
    dummy_person.health_information.infection.symptoms.tag = SymptomTag.hospitalised
    # sim.hospitalise_the_sick(dummy_person, "intensive care")
    hospital = dummy_person.hospital.group
    medical_policies.apply(person=dummy_person, medical_facilities=[hospital])
    sim.activity_manager.move_people_to_active_subgroups(["hospital", "residence"])
    assert dummy_person in hospital[hospital.SubgroupType.patients]
    sim.clear_world()


def test__bury_the_dead(sim: Simulator):
    dummy_person = sim.world.people.members[0]
    sim.bury_the_dead(dummy_person, 0.0)

    assert dummy_person in sim.world.cemeteries.members[0].people
    assert dummy_person.health_information.dead
    assert dummy_person.health_information.infection is None
