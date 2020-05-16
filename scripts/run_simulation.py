from pathlib import Path
import argparse
import time
import matplotlib.pyplot as plt

from june.geography import Geography
from june.demography import Demography
from june.world import World
from june.interaction import DefaultInteraction
from june.infection import Infection
from june.infection.symptoms import SymptomsConstant
from june.infection.transmission import TransmissionConstant
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
from june.simulator import Simulator
from june.seed import Seed


# *********** INITIALIZE WORLD ***************** #

t1 = time.time()
geography = Geography.from_file({"msoa": ["E00088544", "E02002560", "E02002559", "E02003353"]})

geography.hospitals = Hospitals.for_geography(geography)
geography.schools = Schools.for_geography(geography)
geography.cemeteries = Cemeteries()
geography.companies = Companies.for_geography(geography)
geography.care_homes = CareHomes.for_geography(geography)
demography = Demography.for_geography(geography)
world = World(geography, demography, include_households=True)
t2 = time.time()
print(f"Creating the world took {t2 -t1} seconds to run.")

# *********** INITIALIZE SEED ***************** #

symptoms = SymptomsConstant(recovery_rate=0.05)
transmission = TransmissionConstant(probability=0.7)
infection = Infection(transmission, symptoms)
interaction = DefaultInteraction.from_file()
seed = Seed(world.super_areas, infection,)
# Use if you want to seed the disease per region
# with real data
# seed.unleash_virus_per_region()
seed.unleash_virus(2000)

# *********** INITIALIZE SIMULATOR ***************** #
simulator = Simulator.from_file(
    world, interaction, infection, 
)
# update health status of seeded people, depending on symptoms
# class might be unnecessary
simulator.update_health_status(0, 0)
simulator.run()

t3 = time.time()
print(f"Running the simulation took {t3 -t2} seconds to run.")
simulator.logger.plot_infection_curves_per_day()
plt.show()
