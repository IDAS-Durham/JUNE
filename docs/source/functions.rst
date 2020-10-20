.. Note: it is important to keep the current module setting below in
   this file because it prevents any nameclashes with any imports, e.g.
   'june.time' vs. Python's in-built 'time', which otherwise would be
   documented instead.

.. currentmodule:: june


Functions
---------

This lists, and categorises, all functions (not including methods i.e.
functions defined in classes) in `june`. To view methods, find them in
the corresponding class. Note these functions can also be viewed in the
API reference page for the module they are defined within.


`commute_rail_travel`
^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: function.rst

   commute_rail_travel.distribute_passengers


Distributors
^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: function.rst

   distributors.load_sex_per_sector
   distributors.load_workflow_df


HDF5 Savers
^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: function.rst

   hdf5_savers.load_care_homes_from_hdf5
   hdf5_savers.load_companies_from_hdf5
   hdf5_savers.load_geography_from_hdf5
   hdf5_savers.load_hospitals_from_hdf5
   hdf5_savers.load_households_from_hdf5
   hdf5_savers.load_population_from_hdf5
   hdf5_savers.load_schools_from_hdf5
   hdf5_savers.load_universities_from_hdf5
   hdf5_savers.save_care_homes_to_hdf5
   hdf5_savers.save_companies_to_hdf5
   hdf5_savers.save_geography_to_hdf5
   hdf5_savers.save_hospitals_to_hdf5
   hdf5_savers.save_households_to_hdf5
   hdf5_savers.save_population_to_hdf5
   hdf5_savers.save_schools_to_hdf5
   hdf5_savers.save_universities_to_hdf5


Paths
^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: function.rst

   paths.find_default
   paths.path_for_name


Utilities (`utils`)
^^^^^^^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: function.rst

   utils.parse_age_probabilities


World
^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: function.rst

   world._populate_areas
   world.generate_world_from_geography
