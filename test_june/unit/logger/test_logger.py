import copy
from datetime import datetime
from pathlib import Path

import h5py

import numpy as np
import pytest

from june import paths
from june.demography import Person, Population
from june.demography.geography import Geography
from june.groups import Hospital, School, Company, Household, University
from june.groups import (
    Hospitals,
    Schools,
    Companies,
    Households,
    Universities,
    Cemeteries,
)
from june.groups.leisure import leisure, Cinemas, Pubs, Cinema, Pub
from june.infection import SymptomTag
from june.interaction import Interaction
from june.infection.infection import InfectionSelector
from june.infection_seed import InfectionSeed
from june.policy import (
    Policy,
    Quarantine,
    Policies,
    MedicalCarePolicies, InteractionPolicies,
    CloseLeisureVenue,
)
from june.simulator import Simulator
from june.world import World
from june.logger.logger import Logger
from june.logger.read_logger import ReadLogger

from june.demography import Demography

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
test_config = paths.configs_path / "tests/test_simulator_simple.yaml"



@pytest.fixture(name="selector", scope="module")
def create_selector():
    selector = InfectionSelector.from_file()
    selector.recovery_rate = 1.0
    selector.transmission_probability = 1.0
    return selector


@pytest.fixture(name="interaction", scope="module")
def create_interaction():
    interaction = Interaction.from_file()
    interaction.beta['school'] = 0.8
    interaction.beta['cinema'] = 0.0
    interaction.beta['pub'] = 0.0
    interaction.beta['household'] = 10.0
    interaction.alpha_physical = 2.7
    return interaction


@pytest.fixture(name="geog", scope="module")
def create_geography():
    geog = Geography.from_file(filter_key={"area": ["E00000001"]})
    return geog#.super_areas.members[0]

@pytest.fixture(name="world", scope="module")
def make_dummy_world(geog):
    super_area = geog.super_areas.members[0]
    company = Company(super_area=super_area, n_workers_max=100, sector="Q")

    household1 = Household()
    household1.area = super_area.areas[0]
    hospital = Hospital(
        n_beds=40,
        n_icu_beds=5,
        super_area=super_area.name,
        coordinates=super_area.coordinates,
    )
    uni = University(
        coordinates=super_area.coordinates,
        n_students_max=2500,
    )

    worker1 = Person.from_attributes(age=44,sex='f',ethnicity='A1',socioecon_index=5)
    worker1.area = super_area.areas[0]
    household1.add(worker1, subgroup_type=household1.SubgroupType.adults)
    worker1.sector = "Q"
    company.add(worker1)

    worker2 = Person.from_attributes(age=42,sex='m',ethnicity='B1',socioecon_index=5)
    worker2.area = super_area.areas[0]
    household1.add(worker2, subgroup_type=household1.SubgroupType.adults)
    worker2.sector = "Q"
    company.add(worker2)

    student1 = Person.from_attributes(age=20,sex='f',ethnicity='A1',socioecon_index=5)
    student1.area = super_area.areas[0]
    household1.add(student1, subgroup_type=household1.SubgroupType.adults)
    uni.add(student1)

    pupil1 = Person.from_attributes(age=8,sex='m',ethnicity='C1',socioecon_index=5)
    pupil1.area = super_area.areas[0]
    household1.add(pupil1, subgroup_type=household1.SubgroupType.kids)
    #school.add(pupil1)

    pupil2 = Person.from_attributes(age=5,sex='f',ethnicity='A1',socioecon_index=5)
    pupil2.area = super_area.areas[0]
    household1.add(pupil2, subgroup_type=household1.SubgroupType.kids)
    #school.add(pupil2)

    world = World()
    world.schools = Schools([])
    world.hospitals = Hospitals([hospital])
    world.households = Households([household1])
    world.universities = Universities([uni])
    world.companies = Companies([company])
    world.people = Population([worker1, worker2, student1, pupil1, pupil2])
    world.super_areas = geog.super_areas
    world.areas = geog.areas
    world.cemeteries = Cemeteries()
    cinema = Cinema()
    cinema.coordinates = super_area.coordinates
    world.cinemas = Cinemas([cinema])
    pub = Pub()
    pub.coordinates = super_area.coordinates
    world.pubs = Pubs([pub])

    world.areas[0].people = world.people

    return world

@pytest.fixture(name="sim", scope="module")
def create_sim(world,interaction,selector):

    leisure_instance = leisure.generate_leisure_for_config(
        world=world, config_filename=test_config
    )
    leisure_instance.distribute_social_venues_to_households(world.households)
    policies = Policies(
        [
            Quarantine(n_days=5),
            Quarantine(n_days=10),
            CloseLeisureVenue(
                start_time="2020-3-1", 
                end_time="2020-3-30",
                venues_to_close=['pub','cinema'])
        ]
    )
    infection_seed = InfectionSeed(
        super_areas=world.super_areas,selector=selector
    )
    n_cases = 2
    infection_seed.unleash_virus(n_cases)

    sim = Simulator.from_file(
        world=world,
        interaction=interaction,
        infection_selector=selector,
        config_filename=test_config,
        leisure=leisure_instance,
        policies=policies
    )
    return sim


test_dict = {
    'A': 10,
    'B': {
           'B1': {},
    },
}

l = Logger()

def test__log_population(sim):
    sim.logger.log_population(sim.world.people, light_logger=sim.light_logger, chunk_size=2)
    with h5py.File(sim.logger.file_path, "r", libver="latest", swmr=True) as f:
        assert f['population'].attrs['n_people'] == 5
        assert set(f['population/age'][()]) == set([5, 8, 20, 42, 44])
        assert set(f['population/sex'][()]) == set([b'm',b'f'])
        assert set(f['population/ethnicity'][()]) == set([b'A1',b'B1',b'C1'])
        # TODO check more?

def test__log_hospital_characteristics(sim):
    sim.logger.log_hospital_characteristics(sim.world.hospitals)
    with h5py.File(sim.logger.file_path, "r", libver="latest", swmr=True) as f:
        assert set(f['hospitals/n_beds']) == set([40])
        assert set(f['hospitals/n_icu_beds']) == set([5])

def test__log_parameters(sim):
    sim.logger.log_parameters(interaction=sim.interaction, activity_manager=sim.activity_manager)

    with h5py.File(sim.logger.file_path, "r", libver="latest", swmr=True) as f:
        assert f['parameters/beta/school'][()] == 0.8
        assert f['parameters/alpha_physical'][()] == 2.7
        assert f['parameters/policies/quarantine/1/n_days'][()] == 5
        assert f['parameters/policies/quarantine/2/n_days'][()] == 10
        assert (
            set(f['parameters/policies/close_leisure_venue/venues_to_close'][()])
             == set(['cinema','pub'])
        )

def test__log_infected(sim):
    test_datetime = datetime(year=1971,month=1,day=1)
    test_dt_str = test_datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")
    test_ids = [7,8,9,10,11,12]
    test_symptoms = [0,0,1,1,2,3]
    test_nsecondary = [10,9,8,7,6,5]

    sim.logger.log_infected(test_datetime,test_ids,test_symptoms,test_nsecondary)
    with h5py.File(sim.logger.file_path, "r", libver="latest", swmr=True) as f:
        f_ids = f[f'{test_dt_str}/id'][()]
        f_symptoms = f[f'{test_dt_str}/symptoms'][()]
        f_nsecondary = f[f'{test_dt_str}/n_secondary_infections'][()]

    assert set(test_ids) == set(f_ids)
    assert set(test_symptoms) == set(f_symptoms)
    assert set(test_nsecondary) == set(f_nsecondary)

def test__log_infected_in_timestep(sim):
    ### the log_infected function is always called inside do_timestep. So test this too!
    time_steps = []
    for i,time in enumerate(sim.timer):
        time_steps.append(time.strftime("%Y-%m-%dT%H:%M:%S.%f"))
        sim.do_timestep()
        if i > 10:
            break

    with h5py.File(sim.logger.file_path, "r", libver="latest", swmr=True) as f:
        keys = list(f.keys())
        first_ts = time_steps[0]
        infected_set = set(f[f'{first_ts}/id'][()])
        world_ids = set([p.id for p in sim.world.people])

    assert all(t in keys for t in time_steps)
    assert infected_set.issubset( world_ids )
    assert len(infected_set) == 2

