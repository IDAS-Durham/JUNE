# Instructions
1. First run ``create_world.py`` to create a world and save it to ``.hdf5`` format. You can edit
the script to create the region you want. 

2. If you used the default settings, the world will now have been saved in ``tests.hdf5``.
We can now run a simulation using the ``run_parallel_simulation.py`` script. If called serially,
eg, ``python run_parallel_simulation.py`` it will just run in serial, it can be run in parallel doing
``mpirun -np X python run_parallel_simulation.py`` where X is the number of cores.
