"""
This is a quick test that makes sure the box model can be run. It does not check whether it is doing anything correctly,
but at least we can use it in the meantime to make sure the code runs before pusing it to master.
"""

from pathlib import Path
from june.simulator import Simulator
from june import world
from june.time import Timer
from june.geography import Geography
from june.demography import Demography, Person, Population
from june.interaction import Interaction
from june.infection import InfectionSelector
from june.groups.travel import ModeOfTransport, Travel
from june import World
from june.world import generate_world_from_geography
from june.infection_seed import InfectionSeed
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
        person.susceptibility = 1.0
        person.dead = False
    travel = Travel()
    leisure = generate_leisure_for_config(
        world=dummy_world, config_filename=test_config
    )
    interaction = Interaction.from_file(config_filename=interaction_config)
    record = Record(
        record_path=test_results / "results",
    )
    policies = Policies.from_file()
    sim = Simulator.from_file(
        world=world,
        interaction=interaction,
        infection_selector=selector,
        config_filename=test_config,
        leisure=leisure,
        travel=travel,
        policies=policies,
        record=record,
    )
    seed = InfectionSeed(world=sim.world, infection_selector=selector)
    seed.unleash_virus(Population(sim.world.people), n_cases=1)
    sim.run()
    for region in world.regions:
        region.policy["local_closed_venues"] = set()
        region.policy["global_closed_venues"] = set()

