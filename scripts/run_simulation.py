from pathlib import Path
import argparse

from june.world import World
from june.interaction import DefaultInteraction
from june.infection import Infection
from june.infection.symptoms import SymptomsConstant
from june.infection.transmission import TransmissionConstant
from june.simulator import Simulator

parser = argparse.ArgumentParser()
parser.add_argument("--config", default="../../configs/config_boxmode_example.yaml",
        help="path to config file to run", type=str)
args = parser.parse_args()

world = World(config_file = args.config,box_mode=True, box_n_people=1_000)
symptoms = SymptomsConstant(recovery_rate=0.05)
transmission = TransmissionConstant(probability=0.3)
infection = Infection(transmission, symptoms)
interaction = DefaultInteraction.from_file()

simulator = Simulator.from_file(world, interaction, infection, config_filename = args.config)

simulator.seed(world.boxes.members[0], n_infections=100)
simulator.run()

#simulator.logger.plot_infection_curves_per_day()
