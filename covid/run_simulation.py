from covid.world import World
from covid.groups.people.health_index import HealthIndex
from covid.interaction import DefaultInteraction 
from covid.infection import Infection
from covid.infection.symptoms import SymptomsConstant
from covid.infection.transmission import TransmissionConstant
from covid.simulator import Simulator

world = World(box_mode=True, box_n_people=100) 
#TODO: why does it need an specific health_index to initialize
# Should initialize to 0, same with initial time infection or -1
reference_health_index = HealthIndex().get_index_for_age(40)
symptoms = SymptomsConstant(health_index=reference_health_index)
transmission = TransmissionConstant() 
infection = Infection(transmission, symptoms)
interaction = DefaultInteraction()

simulator = Simulator.from_file(world, interaction, infection)

simulator.seed(world.boxes.members[0], n_infections=100)
simulator.run(n_days=50)


