"""
This is a quick test that makes sure the box model can be run. It does not check whether it is doing anything correctly,
but at least we can use it in the meantime to make sure the code runs before pusing it to master.
"""

from pathlib import Path
from june.simulator import Simulator
from june import world
from june.time import Timer
from june.demography.geography import Geography
from june.demography import Demography
import june.interaction as inter
from june.infection import InfectionSelector
from june.groups import Hospitals, Schools, Companies, CareHomes, Cemeteries, Universities
from june.groups.leisure import leisure, Cinemas, Pubs, Groceries
from june.infection import transmission as trans
from june.infection import symptoms as sym
from june import World
from june.world import generate_world_from_geography
from june.infection_seed import InfectionSeed
from june.policy import Policies
from june import paths

from pathlib import Path

selector_config = paths.configs_path / "defaults/infection/InfectionConstant.yaml"
test_config = paths.configs_path / "tests/test_simulator.yaml"


def test_full_run():
    geography = Geography.from_file({"super_area": ["E02002512", "E02001697", "E02004314"]})
                
    geography.hospitals = Hospitals.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.universities = Universities.for_super_areas(geography.super_areas)
    geography.care_homes = CareHomes.for_geography(geography)
    geography.cemeteries = Cemeteries()
    world = generate_world_from_geography(
        geography, include_commute=True, include_households=True
    )
    world.cinemas = Cinemas.for_geography(geography)
    world.pubs = Pubs.for_geography(geography)
    world.groceries = Groceries.for_super_areas(
        geography.super_areas, venues_per_capita=1 / 500
    )
    leisure_instance = leisure.generate_leisure_for_config(
        world=world, config_filename = test_config 
    )
    selector = InfectionSelector.from_file(config_filename=selector_config)
    interaction = inter.ContactAveraging.from_file(selector=selector)
    policies = Policies.from_file()
    simulator = Simulator.from_file(
        world, interaction, selector, config_filename=test_config, leisure=leisure_instance,
        policies=policies
    )
    seed = InfectionSeed(simulator.world.super_areas, selector,)
    seed.unleash_virus(100)
    simulator.run()
