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
from june.groups import Hospitals, Schools, Companies, CareHomes, Cemeteries
from june.infection import transmission as trans
from june.infection import symptoms as sym
from june import World
from june.seed import Seed
from june import paths

from pathlib import Path

selector_config = paths.configs_path / "defaults/infection/InfectionConstant.yaml"
test_config = paths.configs_path / "tests/test_simulator.yaml"

def test_full_run():
    geography = Geography.from_file(
        {"msoa": ["E02002512", "E02001697"]}
    )
    demography = Demography.for_geography(geography)
    geography.hospitals = Hospitals.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.care_homes = CareHomes.for_geography(geography)
    geography.cemeteries = Cemeteries()
    world       = World(geography, demography, include_households=True, include_commute=True)
    selector    = InfectionSelector.from_file(selector_config)
    interaction = inter.DefaultInteraction.from_file()
    interaction.selector = selector
    simulator   = Simulator.from_file(world, interaction, selector,
                                config_filename = test_config)
    seed = Seed(simulator.world.super_areas, selector, )
    seed.unleash_virus(100)
    simulator.run()
    simulator.logger.plot_infection_curves_per_day()
