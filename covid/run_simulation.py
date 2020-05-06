
from covid.world import World
from covid.interaction import InteractionCollective 
from covid.infection import Infection

world = World() 
#TODO: why does it need an specific health_index to initialize
# Should initialize to 0, same with initial time infection or -1
reference_health_index = HealthIndex().get_index_for_age(40)
symptoms = SymptomsConstant(reference_health_index)
transmission = TransmissionConstant() 
infection = Infection(None, transmission, symptoms)
interaction = InteractionCollective()

simulator = Simulator(world, infection, interaction)

simulator.run(n_seed=100, n_days=50)


