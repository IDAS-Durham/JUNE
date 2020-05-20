from pathlib import Path
import argparse
import time
import matplotlib.pyplot as plt

from june.demography.geography import Geography
from june.demography import Demography
from june.world import World
from june.interaction import DefaultInteraction
from june.infection import InfectionSelector, Infection
from june.infection.symptoms import SymptomsConstant
from june.infection.transmission import TransmissionConstant
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
from june.simulator import Simulator
from june.seed import Seed
from june import paths


constant_config = paths.configs_path / "defaults/infection/InfectionConstant.yaml"
test_config = paths.configs_path / "tests/test_simulator.yaml"

# *********** INITIALIZE WORLD ***************** #

t1 = time.time()
geography = Geography.from_file({"msoa":['E02001731', 'E02001709', "E00088544", "E02002560", "E02002559", "E02003353"]})
    

geography.hospitals = Hospitals.for_geography(geography)
geography.schools = Schools.for_geography(geography)
geography.cemeteries = Cemeteries()
geography.companies = Companies.for_geography(geography)
geography.care_homes = CareHomes.for_geography(geography)
demography = Demography.for_geography(geography)
world = World(geography, demography, include_households=True, include_commute=True)
t2 = time.time()
print(f"Creating the world took {t2 -t1} seconds to run.")

# *********** INITIALIZE SEED ***************** #
selector                          = InfectionSelector.from_file(constant_config)
selector.recovery_rate            = 0.05
selector.transmission_probability = 0.7
interaction            = DefaultInteraction.from_file()
interaction.selector   = selector
# *********** INITIALIZE SIMULATOR ***************** #
simulator = Simulator.from_file(world, interaction, selector,
        config_filename = test_config)

simulator.run()

t3 = time.time()
print(f"Running the simulation took {t3 -t2} seconds to run.")
#simulator.logger.plot_infection_curves_per_day()
