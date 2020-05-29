# Create the world
1. First run ``create_world.py`` to create a world and save it to ``.hdf5`` format. You can edit
the script to create the region you want. Note: do not create commute or leisure here.

2. If you used the default settings, the world will now have been saved in ``world.hdf5``.
We can now run a simulation using the ``run_simulation.py`` script. Commute and leisure can be 
added on top of the world if desired. 
To change the simulation settings, you can edit two files:
    - ``config_simulation.yaml`` : config file for time steps and world dynamics.
