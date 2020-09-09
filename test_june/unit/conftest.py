# set seed
import random

import numba as nb
import numpy as np
import pytest

import june.infection.symptoms
from june.interaction import Interaction
from june import paths
from june.demography.geography import Geography, Areas, SuperAreas
from june.commute import ModeOfTransport
from june.groups import *
from june.groups.leisure import *
from june.demography import Person, Population
from june.infection import Infection
from june.infection.infection_selector import InfectionSelector
from june.infection import trajectory_maker as tmaker
from june.infection import transmission as trans
from june.simulator import Simulator
from june.simulator_box import SimulatorBox
from june.world import generate_world_from_geography, World

constant_config = paths.configs_path / "defaults/transmission/TransmissionConstant.yaml"


@pytest.fixture(autouse=True)
def set_random_seed(seed=999):
    """
    Sets global seeds for testing in numpy, random, and numbaized numpy.
    """

    @nb.njit(cache=True)
    def set_seed_numba(seed):
        random.seed(seed)
        return np.random.seed(seed)

    np.random.seed(seed)
    set_seed_numba(seed)
    random.seed(seed)
    return


@pytest.fixture()
def data(pytestconfig):
    return pytestconfig.getoption("data")


@pytest.fixture()
def configs(pytestconfig):
    return pytestconfig.getoption("configs")


@pytest.fixture(name="trajectories", scope="session")
def create_trajectories():
    return tmaker.TrajectoryMakers.from_file()


@pytest.fixture(name="symptoms", scope="session")
def create_symptoms(symptoms_trajectories):
    return symptoms_trajectories


@pytest.fixture(name="symptoms_trajectories", scope="session")
def create_symptoms_trajectories():
    return june.infection.symptoms.Symptoms(
        health_index=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
    )


@pytest.fixture(name="transmission", scope="session")
def create_transmission():
    return trans.TransmissionConstant(probability=0.3)


@pytest.fixture(name="infection", scope="session")
def create_infection(transmission, symptoms):
    return Infection(transmission, symptoms)


@pytest.fixture(name="infection_constant", scope="session")
def create_infection_constant(transmission, symptoms_constant):
    return Infection(transmission, symptoms_constant)


@pytest.fixture(name="interaction", scope="session")
def create_interaction():
    interaction = Interaction.from_file()
    interaction.selector = InfectionSelector.from_file(
        transmission_config_path=constant_config
    )
    return interaction


@pytest.fixture(name="geography", scope="session")
def make_geography():
    geography = Geography.from_file({"super_area": ["E02002512", "E02001697", "E02001731"]})
    return geography


@pytest.fixture(name="world", scope="session")
def create_world(geography):
    geography.hospitals = Hospitals.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.care_homes = CareHomes.for_geography(geography)
    geography.cemeteries = Cemeteries()
    geography.companies = Companies.for_geography(geography)
    world = generate_world_from_geography(geography, include_households=True)
    return world


# @pytest.fixture(name="simulator", scope="session")
# def create_simulator(world, interaction, infection_constant, selector):
#    return Simulator.from_file(world=world, interaction=interaction, infection_constant, infection_selector=selector)
#


@pytest.fixture(name="world_box", scope="session")
def create_box_world():
    geography = Geography.from_file({"area": ["E00000697"]})
    return generate_world_from_geography(geography, box_mode=True)


@pytest.fixture(name="selector", scope="session")
def make_selector():
    return InfectionSelector.from_file(transmission_config_path=constant_config)


@pytest.fixture(name="simulator_box", scope="session")
def create_simulator_box(world_box, interaction, selector):
    config_file = paths.configs_path / "config_boxmode_example.yaml"
    return SimulatorBox.from_file(
        world=world_box,
        interaction=interaction,
        config_filename=config_file,
        infection_selector=selector,
    )


@pytest.fixture(name="world_visits", scope="session")
def make_super_areas():
    geo = Geography.from_file({"super_area": ["E02003353", "E02002512"]})
    geo.care_homes = CareHomes.for_geography(geo)
    world = generate_world_from_geography(geo, include_households=True)
    return world


# policy dummy world
@pytest.fixture(name="dummy_world", scope="session")
def make_dummy_world():
    g = Geography.from_file(filter_key={"super_area": ["E02002512", "E02001697", "E02001731"]})
    super_area = g.super_areas.members[0]
    area = g.areas.members[0]
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
    hospital = Hospital(
        n_beds=40,
        n_icu_beds=5,
        super_area=super_area,
        coordinates=super_area.coordinates,
    )
    worker = Person.from_attributes(age=40)
    worker.area = super_area.areas[0]
    household.add(worker, subgroup_type=household.SubgroupType.adults)
    worker.sector = "Q"
    company.add(worker)

    pupil = Person.from_attributes(age=6)
    pupil.area = super_area.areas[0] 
    household.add(pupil, subgroup_type=household.SubgroupType.kids)
    household.area = super_area.areas[0] 
    school.add(pupil)

    student = Person.from_attributes(age=21)
    student.area = super_area.areas[0] 
    household.add(student, subgroup_type=household.SubgroupType.adults)
    university = University(coordinates=super_area.coordinates, n_students_max=100,)
    university.add(student)

    commuter = Person.from_attributes(sex="m", age=30)
    commuter.area = super_area.areas[0]
    commuter.mode_of_transport = ModeOfTransport(description="bus", is_public=True)
    commuter.mode_of_transport = "public"
    household.add(commuter)

    world = World()
    world.schools = Schools([school])
    world.hospitals = Hospitals([hospital])
    world.households = Households([household])
    world.universities = Universities([])
    world.companies = Companies([company])
    world.universities = Universities([university])
    world.care_homes = CareHomes([CareHome()])
    world.people = Population([worker, pupil, student, commuter])
    world.areas = Areas([super_area.areas[0]])
    world.areas[0].people = world.people
    world.super_areas = SuperAreas([super_area])
    cinema = Cinema()
    cinema.coordinates = super_area.coordinates
    world.cinemas = Cinemas([cinema])
    pub = Pub()
    pub.coordinates = super_area.coordinates
    world.pubs = Pubs([pub])
    grocery = Grocery()
    grocery.coordinates = super_area.coordinates
    world.groceries = Groceries([grocery])
    # commute
    world.commutecities = CommuteCities.for_super_areas(world.super_areas)
    world.commutecities[7].add(commuter)
    world.commutehubs = CommuteHubs(world.commutecities)
    world.commutehubs.from_file()
    world.commutehubs.init_hubs()
    world.commutehubs[0].commute_through.append(commuter)
    world.commuteunits = CommuteUnits(world.commutehubs.members)
    world.commuteunits.init_units()
    world.commutecityunits = CommuteCityUnits(world.commutecities.members)
    world.cemeteries = Cemeteries()
    return world


@pytest.fixture(name="policy_simulator", scope="session")
def make_policy_simulator(dummy_world, interaction, selector):
    config_name = paths.configs_path / "tests/test_simulator_simple.yaml"
    sim = Simulator.from_file(
        dummy_world,
        interaction,
        infection_selector=selector,
        config_filename=config_name,
        save_path=None,
        policies=None,
        leisure=None,
    )
    return sim


@pytest.fixture(name="setup_policy_world")
def setup_world(dummy_world, policy_simulator):
    world = dummy_world
    worker = world.people[0]
    pupil = world.people[1]
    student = world.people[2]
    student.lockdown_status = None
    worker.lockdown_status = None
    policy_simulator.timer.reset()
    policy_simulator.clear_world()
    for household in world.households:
        household.quarantine_starting_date = None
    for person in [pupil, student, worker]:
        person.infection = None
        person.susceptibility = 1.0
        person.dead = False
        person.subgroups.medical_facility = None
    return world, pupil, student, worker, policy_simulator
