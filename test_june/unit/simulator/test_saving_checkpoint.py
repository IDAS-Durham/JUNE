import pytest
import h5py
import numpy as np
import datetime
import logging
import june.simulator

from june.logger import Logger
from june.groups import Hospitals, Hospital
from june.demography import Demography, Population
from june.geography import Geography
from june.geography import Areas
from june.world import generate_world_from_geography
from june.hdf5_savers import generate_world_from_hdf5
from june.groups.travel import Travel, generate_commuting_network
from june.policy import Policies
from june.interaction import Interaction
from june.simulator import Simulator
from june.infection.symptoms import SymptomTag
from june.infection_seed import InfectionSeed
from june.infection.transmission_xnexp import TransmissionXNExp
from june.infection.transmission import TransmissionGamma
from june import paths


from june.hdf5_savers.checkpoint_saver import (
    _save_transmissions_to_hdf5,
    _load_transmissions_from_hdf5,
)

test_config = paths.configs_path / "tests/test_checkpoint_config.yaml"


class TestTransmissionSavers:
    def test__save_xnexp(self):
        with h5py.File("checkpoint_tests.hdf5", "w") as f:
            pass
        transmission1 = TransmissionXNExp(
            max_probability=1,
            time_first_infectious=1,
            norm_time=2,
            n=3,
            alpha=4,
            max_symptoms="asymptomatic",
            asymptomatic_infectious_factor=5,
            mild_infectious_factor=6,
        )
        transmission2 = TransmissionXNExp(
            max_probability=7,
            time_first_infectious=8,
            norm_time=9,
            n=10,
            alpha=11,
            max_symptoms="mild",
            asymptomatic_infectious_factor=12,
            mild_infectious_factor=13,
        )
        transmissions = [transmission1, transmission2]
        _save_transmissions_to_hdf5(
            "checkpoint_tests.hdf5", transmissions, chunk_size=1
        )
        transmissions_recovered = _load_transmissions_from_hdf5(
            "checkpoint_tests.hdf5", chunk_size=1
        )
        for transmission, transmissions_recovered in zip(
            transmissions_recovered, transmissions
        ):
            for attribute in [
                "time_first_infectious",
                "norm_time",
                "n",
                "norm",
                "alpha",
                "probability",
            ]:
                assert getattr(transmission, attribute) == getattr(
                    transmissions_recovered, attribute
                )


def _populate_areas(areas: Areas, demography):
    people = Population()
    for area in areas:
        area.populate(demography)
        people.extend(area.people)
    return people


def create_world():
    geography = Geography.from_file({"area": ["E00003282", "E00003283"]})
    demography = Demography.for_geography(geography)
    geography.hospitals = Hospitals(
        [
            Hospital(
                n_beds=1000,
                n_icu_beds=1000,
                super_area=geography.super_areas[0],
                coordinates=geography.areas[0].coordinates,
            )
        ]
    )
    world = generate_world_from_geography(geography=geography, include_households=True)
    return world


def run_simulator(selector):
    world = create_world()
    world.to_hdf5("./checkpoint_world.hdf5")
    # restore health status of people
    for person in world.people:
        person.infection = None
        person.susceptibility = 1.0
        person.dead = False
    interaction = Interaction.from_file()
    policies = Policies([])
    logger = Logger(save_path="tests")
    sim = Simulator.from_file(
        world=world,
        interaction=interaction,
        infection_selector=selector,
        config_filename=test_config,
        leisure=None,
        logger=logger,
        policies=policies,
    )
    seed = InfectionSeed(sim.world, selector)
    seed.unleash_virus(sim.world.people, n_cases=20)
    sim.run()
    return sim


def test__checkpoints_are_saved(selector):
    june.simulator.output_logger.disabled = True
    sim = run_simulator(selector)
    fresh_world = generate_world_from_hdf5("./checkpoint_world.hdf5")
    interaction = Interaction.from_file()
    policies = Policies([])
    logger = Logger(save_path="tests")
    sim_recovered = Simulator.from_checkpoint(
        world=fresh_world,
        checkpoint_path="tests/checkpoint_2020-03-25.pkl",
        interaction=interaction,
        infection_selector=selector,
        config_filename=test_config,
        leisure=None,
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
