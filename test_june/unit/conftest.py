import random

import numba as nb
import numpy as np
import pytest
import h5py
from pathlib import Path

import june.infection.symptoms
from june.interaction import Interaction
from june import paths
from june.geography import (
    Geography,
    Areas,
    SuperAreas,
    Regions,
    Cities,
    City,
    Station,
    Stations,
)
from june.geography.station import CityStation, InterCityStation
from june.groups.travel import (
    ModeOfTransport,
    CityTransport,
    CityTransports,
    InterCityTransport,
    InterCityTransports,
)
from june.groups import *
from june.groups.leisure import *
from june.groups.travel import Travel
from june.demography import Person, Population
from june.infection import Infection, Symptoms, TrajectoryMakers
from june.infection.infection_selector import InfectionSelector
from june.infection import transmission as trans
from june.simulator import Simulator
from june.simulator_box import SimulatorBox
from june.world import generate_world_from_geography, World

constant_config = paths.configs_path / "defaults/transmission/TransmissionConstant.yaml"
interaction_config = paths.configs_path / "tests/interaction.yaml"

import logging

# disable logging for testing
logging.disable(logging.CRITICAL)


@pytest.fixture(autouse=True, name="test_results", scope="session")
def make_test_output():
    save_path = Path("./test_results")
    save_path.mkdir(exist_ok=True)
    return save_path


@pytest.fixture(autouse=True)
def set_random_seed(seed=999):
    """
    Sets global seeds for testing in numpy, random, and numbaized numpy.
    """

    @nb.njit(cache=True)
    def set_seed_numba(seed):
        random.seed(seed)
        np.random.seed(seed)

    set_seed_numba(seed)
    np.random.seed(seed)
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
    return TrajectoryMakers.from_file()


@pytest.fixture(name="symptoms", scope="session")
def create_symptoms(symptoms_trajectories):
    return symptoms_trajectories


@pytest.fixture(name="health_index_generator", scope="session")
def make_hi():
    return lambda person: [0.4, 0.5, 0.7, 0.74, 0.85, 0.90, 0.95]


@pytest.fixture(name="symptoms_trajectories", scope="session")
def create_symptoms_trajectories():
    return Symptoms(
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
def create_interaction(health_index_generator):
    interaction = Interaction.from_file(config_filename=interaction_config)
    interaction.selector = InfectionSelector(
        transmission_config_path=constant_config,
        health_index_generator=health_index_generator,
    )
    return interaction


@pytest.fixture(name="geography", scope="session")
def make_geography():
    geography = Geography.from_file(
        {"super_area": ["E02002512", "E02001697", "E02001731"]}
    )
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


@pytest.fixture(name="world_box", scope="session")
def create_box_world():
    geography = Geography.from_file({"area": ["E00000697"]})
    return generate_world_from_geography(geography, box_mode=True)


@pytest.fixture(name="selector", scope="session")
def make_selector(health_index_generator):
    return InfectionSelector(
        transmission_config_path=constant_config,
        health_index_generator=health_index_generator,
    )


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
    geo = Geography.from_file({"super_area": ["E02003353"]})
    geo.care_homes = CareHomes.for_geography(geo)
    world = generate_world_from_geography(geo, include_households=True)
    return world


# policy dummy world
@pytest.fixture(name="dummy_world", scope="session")
def make_dummy_world():
    g = Geography.from_file(filter_key={"super_area": ["E02002559"]})
    super_area = g.super_areas.members[0]
    area = g.areas.members[0]
    company = Company(super_area=super_area, n_workers_max=100, sector="S")
    school = School(
        coordinates=super_area.coordinates,
        n_pupils_max=100,
        age_min=4,
        age_max=10,
        sector="primary",
        area=area,
    )
    household = Household()
    household.area = super_area.areas[0]
    hospital = Hospital(
        n_beds=40, n_icu_beds=5, area=area, coordinates=super_area.coordinates,
    )
    super_area.closest_hospitals = [hospital]
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
    university = University(
        coordinates=super_area.coordinates, n_students_max=100, area=area
    )
    university.add(student)

    commuter = Person.from_attributes(sex="m", age=30)
    commuter.area = super_area.areas[0]
    commuter.work_super_area = super_area
    commuter.mode_of_transport = ModeOfTransport(description="surf", is_public=True)
    household.add(commuter)

    world = World()
    world.schools = Schools([school])
    world.hospitals = Hospitals([hospital])
    world.households = Households([household])
    world.universities = Universities([])
    world.companies = Companies([company])
    world.universities = Universities([university])
    world.care_homes = CareHomes([CareHome(area=area)])
    world.people = Population([worker, pupil, student, commuter])
    world.areas = Areas([super_area.areas[0]])
    world.areas[0].people = world.people
    world.super_areas = SuperAreas([super_area])
    world.regions = Regions([super_area.region])
    cinema = Cinema(area=area)
    cinema.coordinates = super_area.coordinates
    cinema.area = area
    world.cinemas = Cinemas([cinema])
    pub = Pub(area=area)
    pub.coordinates = super_area.coordinates
    pub.area = area
    world.pubs = Pubs([pub])
    grocery = Grocery(area=area)
    grocery.coordinates = super_area.coordinates
    grocery.area = area
    world.groceries = Groceries([grocery])
    city = City(name="test", coordinates=[1, 2])
    world.cities = Cities([city])
    city.internal_commuter_ids.add(commuter.id)
    city.city_stations = [CityStation(super_area=world.super_areas[0], city=city)]
    world.stations = city.city_stations
    station = city.city_stations[0]
    super_area.city = city
    # world.super_areas[0].closest_inter_city_station_for_city[city.name] = station
    city_transports = CityTransports([CityTransport(station=station)])
    world.city_transports = city_transports
    inter_city_transports = InterCityTransports([InterCityTransport(station=station)])
    world.inter_city_transports = inter_city_transports
    station.city_transports = city_transports
    station.inter_city_transports = inter_city_transports
    world.cemeteries = Cemeteries()
    return world


@pytest.fixture(name="policy_simulator", scope="session")
def make_policy_simulator(dummy_world, interaction, selector):
    config_name = paths.configs_path / "tests/test_simulator_simple.yaml"
    travel = Travel()
    sim = Simulator.from_file(
        dummy_world,
        interaction,
        infection_selector=selector,
        config_filename=config_name,
        record=None,
        travel=travel,
        policies=None,
        leisure=None,
    )
    return sim


@pytest.fixture(name="setup_policy_world")
def setup_world(dummy_world, policy_simulator):
    world = dummy_world
    world.regions[0].regional_compliance = 1
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


@pytest.fixture(name="full_world_geography", scope="session")
def make_full_world_geography():
    geography = Geography.from_file({"super_area": ["E02001731", "E02002566"]})
    return geography


@pytest.fixture(name="full_world", scope="session")
def create_full_world(full_world_geography, test_results):
    # clean file
    with h5py.File(test_results / "test.hdf5", "w") as f:
        pass
    geography = full_world_geography
    geography.hospitals = Hospitals.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    geography.care_homes = CareHomes.for_geography(geography)
    geography.universities = Universities.for_geography(geography)
    world = generate_world_from_geography(geography=geography, include_households=True)
    world.pubs = Pubs.for_geography(geography)
    world.cinemas = Cinemas.for_geography(geography)
    world.groceries = Groceries.for_geography(geography)
    leisure = generate_leisure_for_world(
        ["pubs", "cinemas", "groceries", "household_visits", "care_home_visits"], world
    )
    leisure.distribute_social_venues_to_areas(
        areas=world.areas, super_areas=world.super_areas
    )
    travel = Travel()
    travel.initialise_commute(world)
    return world


@pytest.fixture(name="domains_world", scope="session")
def create_domains_world():
    geography = Geography.from_file(
        {"super_area": ["E02001731", "E02001732", "E02002566", "E02002567"]}
    )
    geography.hospitals = Hospitals.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    geography.care_homes = CareHomes.for_geography(geography)
    geography.universities = Universities.for_geography(geography)
    world = generate_world_from_geography(geography=geography, include_households=True)
    world.pubs = Pubs.for_geography(geography)
    world.cinemas = Cinemas.for_geography(geography)
    world.groceries = Groceries.for_geography(geography)
    leisure = generate_leisure_for_world(
        ["pubs", "cinemas", "groceries", "household_visits", "care_home_visits"], world
    )
    leisure.distribute_social_venues_to_areas(
        areas=world.areas, super_areas=world.super_areas
    )
    travel = Travel()
    travel.initialise_commute(world)
    return world
