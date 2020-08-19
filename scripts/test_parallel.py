from june.hdf5_savers import generate_world_from_hdf5
from june import World
from mpi4py import MPI
from june.parallel import parallel_update, parallel_setup

world_file = "./tests.hdf5"
config_path = "./config_simulation.yaml"

world = generate_world_from_hdf5(world_file, chunk_size=1_000_000)
print("World loaded successfully")

# add parallelism
World.parallel_setup = parallel_setup
World.parallel_update = parallel_update
# FIXME: better to do this with a config file ... but this is stub code:
comm = MPI.COMM_WORLD
world.parallel_setup(comm)
