import pytest
import datetime
from june.demography.geography import Geography
from june.demography import Demography
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
from june.interaction import DefaultInteraction
from june.infection import SymptomTags, SymptomsConstant
from june.infection import InfectionSelector, Infection
from june.simulator import Simulator
from june.world import World
from june import paths
from june.simulator_logger import Logger

constant_config = paths.configs_path / "defaults/infection/InfectionConstant.yaml"
test_config = paths.configs_path / "tests/test_simulator_simple.yaml"


@pytest.fixture(name="simple_sim", scope="module")
def create_simulator():
    geography = Geography.from_file({"msoa": ["E02002559"]})
    geography.hospitals = Hospitals.for_geography(geography)
    geography.cemeteries = Cemeteries()
    geography.care_homes = CareHomes.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    demography = Demography.for_geography(geography)
    world = World(geography, demography, include_households=True)
    selector = InfectionSelector.from_file(constant_config)
    selector.recovery_rate = 0.0
    selector.transmission_probability = 0.7
    interaction = DefaultInteraction.from_file()
    interaction.selector = selector
    return Simulator.from_file(
        world, interaction, selector, config_filename=test_config
    )


def test__initialize_dict(simple_sim):
    infection_keys = [
        "infected",
        "recovered",
        "susceptible",
        "hospitalised",
        "intensive_care",
    ]
    age_range = [0, 50, 100]
    logger = Logger(
        simple_sim,
        simple_sim.world,
        simple_sim.timer,
        age_range=age_range,
        infection_keys=infection_keys,
    )

    area_dict = logger.initialize_area_dict(logger.world.areas.members)
    assert list(area_dict.keys()) == [
        area.name for area in simple_sim.world.areas.members
    ]

    example_area = simple_sim.world.areas.members[0]
    assert list(area_dict[example_area.name].keys()) == ["f", "m"]
    assert list(area_dict[example_area.name]["f"].keys()) == ["0-49", "50-99"]
    assert list(area_dict[example_area.name]["f"]["0-49"].keys()) == infection_keys


def test__age_key(simple_sim):
    infection_keys = [
        "infected",
        "recovered",
        "susceptible",
        "hospitalised",
        "intensive_care",
    ]
    age_range = [0, 50, 100]
    logger = Logger(
        simple_sim,
        simple_sim.world,
        simple_sim.timer,
        age_range=age_range,
        infection_keys=infection_keys,
    )

    area_dict = logger.initialize_area_dict(logger.world.areas.members)
    assert logger.get_age_key(0) == "0-49"
    assert logger.get_age_key(45) == "0-49"
    assert logger.get_age_key(50) == "50-99"
    assert logger.get_age_key(98) == "50-99"


def test__populate_dict_with_susceptibles(simple_sim):
    infection_keys = [
        "infected",
        "recovered",
        "susceptible",
        "hospitalised",
        "intensive_care",
    ]
    age_range = [0, 50, 100]
    logger = Logger(
        simple_sim, simple_sim.world, simple_sim.timer, age_range, infection_keys
    )
    area_dict = logger.initialize_area_dict(logger.world.areas.members)

    example_area = simple_sim.world.areas.members[0]
    example_dict = area_dict[example_area.name]
    logger.log_area(example_area, example_dict)
    n_susceptible = 0
    for sex in ["m", "f"]:
        for age in example_dict[sex].keys():
            for infection_key in infection_keys:
                if infection_key != "susceptible":
                    assert example_dict[sex][age][infection_key] == 0
                else:
                    n_susceptible += example_dict[sex][age][infection_key]

    assert n_susceptible == len(example_area.people)


def test__populate_dict_with_hospitalised(simple_sim):
    infection_keys = [
        "infected",
        "recovered",
        "susceptible",
        "hospitalised",
        "intensive_care",
    ]
    age_range = [0, 50, 100]
    logger = Logger(
        simple_sim, simple_sim.world, simple_sim.timer, age_range, infection_keys
    )
    area_dict = logger.initialize_area_dict(logger.world.areas.members)

    example_area = simple_sim.world.areas.members[0]
    # Send dummy to hospital
    dummy_person = example_area.people[0]
    simple_sim.selector.infect_person_at_time(dummy_person, 0.0)
    dummy_person.health_information.infection.symptoms.tag = SymptomTags.hospitalised

    # Send dummy to ICU
    dummy_person_icu = example_area.people[1]
    simple_sim.selector.infect_person_at_time(dummy_person_icu, 0.0)
    dummy_person_icu.health_information.infection.symptoms.tag = (
        SymptomTags.intensive_care
    )

    simple_sim.update_health_status(0.0, 0.0)
    example_dict = area_dict[example_area.name]
    logger.log_area(example_area, example_dict)
    n_hospitalised = 0
    n_icu_hospitalised = 0
    n_infected = 0
    for sex in ["m", "f"]:
        for age in example_dict[sex].keys():
            for infection_key in infection_keys:
                if infection_key == "recovered":
                    assert example_dict[sex][age][infection_key] == 0
                elif infection_key == "hospitalised":
                    n_hospitalised += example_dict[sex][age][infection_key]
                elif infection_key == "intensive_care":
                    n_icu_hospitalised += example_dict[sex][age][infection_key]
                elif infection_key == "infected":
                    n_infected += example_dict[sex][age][infection_key]

    assert n_hospitalised == 1
    assert n_icu_hospitalised == 1
    assert n_infected == n_hospitalised + n_icu_hospitalised


def test__time_step(simple_sim):
    infection_keys = [
        "infected",
        "recovered",
        "susceptible",
        "hospitalised",
        "intensive_care",
    ]
    age_range = [0, 50, 101]
    logger = Logger(
        simple_sim, simple_sim.world, simple_sim.timer, age_range, infection_keys
    )
    logger.log_timestep(simple_sim.timer.date, simple_sim.world.areas)
    assert list(logger.output_dict.keys())[0] == simple_sim.timer.date
    next(simple_sim.timer)
    logger.log_timestep(simple_sim.timer.date, simple_sim.world.areas)

    assert list(logger.output_dict.keys())[
        1
    ] == simple_sim.timer.initial_date + datetime.timedelta(days=1)
    assert list(logger.output_dict.keys())[1] == simple_sim.timer.date
