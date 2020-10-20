import pytest
import h5py
import numpy as np
import datetime
import logging
import june.simulator
from pathlib import Path
from random import randint

from june.records import Record 
from june.groups import Hospitals, Hospital
from june.demography import Population, Person
from june.geography import Area, Areas, SuperArea, SuperAreas
from june.groups import Households, Household
from june.world import World
from june.groups import Cemeteries
from june.geography import Geography
from june.geography import Areas
from june.hdf5_savers import generate_world_from_hdf5
from june.groups.travel import Travel 
from june.policy import Policies
from june.interaction import Interaction
from june.simulator import Simulator
from june.infection.symptoms import SymptomTag
from june.infection_seed import InfectionSeed
from june.infection.transmission_xnexp import TransmissionXNExp
from june.infection.transmission import TransmissionGamma
from june import paths

test_config = paths.configs_path / "tests/test_checkpoint_config.yaml"
config_interaction = paths.configs_path / "tests/interaction.yaml"


def _populate_areas(areas: Areas):
    people = Population()
    k = 0
    for area in areas:
        for i in range(12):
            ages = np.arange(0, 120, 10)
            person = Person.from_attributes(sex="f", age=ages[i], id=k)
            person.area = area
            k += 1
            area.people.append(person)
        people.extend(area.people)
    return people


def _create_households(areas: Areas):
    households = []
    for area in areas:
        k = 0
        for i in range(12):
            household = Household()
            household.add(area.people[k])
            households.append(household)
            k += 1
    return Households(households)


def create_world():
    areas = []
    super_areas = []
    for i in range(2):
        areass = []
        for j in range(5):
            area = Area()
            areass.append(area)
            areas.append(area)
        super_area = SuperArea(areas=areass, name="asd")
        for area in areass:
            area.super_area = super_area
        super_areas.append(super_area)
    areas = Areas(areas, ball_tree=False)
    super_areas = SuperAreas(super_areas, ball_tree=False)
    world = World()
    world.people = _populate_areas(areas)
    world.households = _create_households(areas)
    world.areas = areas
    world.super_areas = super_areas
    world.hospitals = Hospitals(
        [Hospital(n_beds=1000, n_icu_beds=1000, area=None, coordinates=None,)],
        ball_tree=False,
    )
    world.cemeteries = Cemeteries()
    return world


def run_simulator(selector, test_results):
    world = create_world()
    interaction = Interaction.from_file(config_filename=config_interaction)
    policies = Policies([])
    sim = Simulator.from_file(
        world=world,
        interaction=interaction,
        infection_selector=selector,
        config_filename=test_config,
        leisure=None,
        policies=policies,
        checkpoint_path=test_results / 'checkpoint_tests',
    )
    seed = InfectionSeed(sim.world, selector)
    seed.unleash_virus(sim.world.people, n_cases=50)
    sim.run()
    return sim


class TestCheckpoints:
    def test__checkpoints_are_saved(self, selector, test_results):
        checkpoint_folder = Path(test_results / "checkpoint_tests")
        checkpoint_folder.mkdir(exist_ok=True, parents=True)
        sim = run_simulator(selector, test_results)
        assert len(sim.world.people.infected) > 0
        assert len(sim.world.people.recovered) > 0
        assert len(sim.world.people.susceptible) > 0
        assert len(sim.world.people.dead) > 0
        fresh_world = create_world()
        interaction = Interaction.from_file(config_filename=config_interaction)
        policies = Policies([])
        sim_recovered = Simulator.from_checkpoint(
            world=fresh_world,
            checkpoint_path=checkpoint_folder / "checkpoint_2020-03-25.hdf5",
            interaction=interaction,
            infection_selector=selector,
            config_filename=test_config,
            leisure=None,
            travel=None,
            policies=policies,
        )
        # check timer is correct
        assert sim_recovered.timer.initial_date == sim.timer.initial_date
        assert sim_recovered.timer.final_date == sim.timer.final_date
        assert sim_recovered.timer.now == sim.timer.now
        assert sim_recovered.timer.date.date() == datetime.datetime(2020, 3, 26).date()
        assert sim_recovered.timer.shift == sim.timer.shift
        assert sim_recovered.timer.delta_time == sim.timer.delta_time
        for person1, person2 in zip(sim.world.people, sim_recovered.world.people):
            assert person1.id == person2.id
            if person1.infection is not None:
                assert person2.infection is not None
                inf1 = person1.infection
                inf2 = person2.infection
                assert inf1.start_time == inf1.start_time
                assert inf1.infection_probability == inf2.infection_probability
                assert inf1.number_of_infected == inf2.number_of_infected
                assert inf1.transmission.probability == inf2.transmission.probability
                assert inf1.symptoms.tag == inf2.symptoms.tag
                continue
            assert person1.susceptible == person2.susceptible
            assert person1.infected == person2.infected
            assert person1.recovered == person2.recovered
            assert person1.susceptibility == person2.susceptibility
            assert person1.dead == person2.dead
        # clean up
