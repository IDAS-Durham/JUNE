from pathlib import Path
from june.simulator import Simulator
from june import world
from june.time import Timer
from june.geography import Geography
from june.demography import Demography, Person, Population
from june.interaction import Interaction
from june.epidemiology.infection import InfectionSelectors, Immunity
from june.epidemiology.infection_seed import InfectionSeed
from june.epidemiology.epidemiology import Epidemiology
from june.groups.travel import ModeOfTransport, Travel
from june import World
from june.world import generate_world_from_geography
from june.policy import Policies
from june.records import Record
from june.groups.leisure import generate_leisure_for_config
from june import paths

from pathlib import Path

selector_config = paths.configs_path / "defaults/infection/InfectionConstant.yaml"
test_config = paths.configs_path / "tests/test_simulator.yaml"
interaction_config = paths.configs_path / "tests/interaction.yaml"


def test__full_run(dummy_world, selector, test_results):
    world = dummy_world
    # restore health status of people
    for person in world.people:
        person.infection = None
        person.immunity = Immunity()
        person.dead = False
        print(person.residence.group.residences_to_visit)
    travel = Travel()
    leisure = generate_leisure_for_config(
        world=dummy_world, config_filename=test_config
    )
    interaction = Interaction.from_file(config_filename=interaction_config)
    record = Record(
        record_path=test_results / "results",
    )
    policies = Policies.from_file()
    selectors = InfectionSelectors([selector])
    epidemiology = Epidemiology(infection_selectors=selectors)

    sim = Simulator.from_file(
        world=world,
        interaction=interaction,
        epidemiology=epidemiology,
        config_filename=test_config,
        leisure=leisure,
        travel=travel,
        policies=policies,
        record=record,
    )
    seed = InfectionSeed.from_uniform_cases(world=sim.world, infection_selector=selector, cases_per_capita=0.01, date=sim.timer.date_str)
    seed.unleash_virus_per_day(date=sim.timer.date, time=0)
    sim.run()
    for region in world.regions:
        region.policy["local_closed_venues"] = set()
        region.policy["global_closed_venues"] = set()

