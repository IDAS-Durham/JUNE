from pathlib import Path

from june.world import World
from june.demography.health_index import HealthIndex
from june.interaction import DefaultInteraction 
from june.infection import Infection
from june.infection.symptoms import SymptomsConstant
from june.infection.transmission import TransmissionConstant
from june.simulator import Simulator

config_file = "../configs/config_boxmode_example.yaml"
world = World(config_file = config_file,box_mode=True, box_n_people=1_000) 
#TODO: why does it need an specific health_index to initialize
# Should initialize to 0, same with initial time infection or -1
reference_health_index = HealthIndex().get_index_for_age(40)
symptoms = SymptomsConstant(health_index=reference_health_index, recovery_rate=0.05)
transmission = TransmissionConstant(probability=0.3) 
infection = Infection(transmission, symptoms)
interaction = DefaultInteraction.from_file()

simulator = Simulator.from_file(world, interaction, infection, config_filename = config_file)

simulator.seed(world.boxes.members[0], n_infections=100)
simulator.run()
simulator.logger.plot_infection_curves_per_day()


