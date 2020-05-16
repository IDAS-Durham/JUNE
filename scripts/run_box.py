from pathlib import Path
import argparse
import time

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

parser = argparse.ArgumentParser()
parser.add_argument(
    "--config",
    default="box_simulator.yaml",
    help="path to config file to run",
    type=str,
)
args = parser.parse_args()


# *********** INITIALIZE WORLD ***************** #

t1 = time.time()
geography = Geography.from_file(
    {"msoa": ["E02003999"]}
)
world = World.from_geography(geography, box_mode=True)
t2 = time.time()
print(f"Creating the world took {t2 -t1} seconds to run.")


# *********** INITIALIZE SEED ***************** #

symptoms = SymptomsConstant(recovery_rate=0.05)
transmission = TransmissionConstant(probability=0.3)
infection = Infection(transmission, symptoms)
interaction = DefaultInteraction.from_file()
seed = Seed(world.boxes, infection, )
# Use if you want to seed the disease per region
# with real data
#seed.unleash_virus_per_region()
seed.unleash_virus(100, box_mode=True)

# *********** INITIALIZE SIMULATOR ***************** #
simulator = Simulator.from_file(
    world, interaction, infection, config_filename=args.config
)
# update health status of seeded people, depending on symptoms
# class might be unnecessary

#simulator.update_health_status(0,0)

simulator.run()

t3 = time.time()
print(f"Running the simulation took {t3 -t2} seconds to run.")
simulator.logger.plot_infection_curves_per_day()
