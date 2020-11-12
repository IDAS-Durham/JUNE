.. Note: it is important to keep the current module setting below in
   this file because it prevents any nameclashes with any imports, e.g.
   'june.time' vs. Python's in-built 'time', which otherwise would be
   documented instead.

.. currentmodule:: june


Modules
-------

This lists, and categorises, all modules, where for a given module all
members of that module (classes, functions, etc.) are shown, including
those that are not (yet) documented.


Package `__init__`-based modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::
   Most of the modules listed in this particular section just contain
   a package `__init__` with some imports, hence only their names as titles
   will be rendered on the corresponding reference pages.

   However such modules are left in this listing for completeness (note
   also that if any are left out, the Sphinx build will give a warning).


.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   activity
   box
   demography
   distributors
   geography
   groups
   groups.commute
   groups.group
   groups.leisure
   groups.travel
   hdf5_savers
   infection
   infection_seed
   interaction
   logger
   policy
   records
   utils
   visualization


Activity
^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   activity.activity_manager_box
   activity.activity_manager


Box
^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   box.box_mode


Demography
^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   demography.demography
   demography.person


Distributors
^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   distributors.care_home_distributor
   distributors.company_distributor
   distributors.hospital_distributor
   distributors.household_distributor
   distributors.school_distributor
   distributors.university_distributor
   distributors.worker_distributor


Exceptions (`exc`)
^^^^^^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   exc


Geography
^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   geography.city
   geography.geography
   geography.station


Groups
^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   groups.boundary
   groups.care_home
   groups.cemetery
   groups.company
   groups.hospital
   groups.household
   groups.school
   groups.university

See also the sub-sections grouping together related types of `Groups`.


Group Groups
""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   groups.group.abstract
   groups.group.external
   groups.group.group
   groups.group.subgroup
   groups.group.supergroup


Leisure Groups
""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   groups.leisure.care_home_visits
   groups.leisure.cinema
   groups.leisure.grocery
   groups.leisure.household_visits
   groups.leisure.leisure
   groups.leisure.pub
   groups.leisure.social_venue_distributor
   groups.leisure.social_venue


Travel Groups
"""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   groups.travel
   groups.travel.mode_of_transport
   groups.travel.transport
   groups.travel.travel


HDF5 Savers
^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   hdf5_savers.carehome_saver
   hdf5_savers.commute_saver
   hdf5_savers.company_saver
   hdf5_savers.geography_saver
   hdf5_savers.hospital_saver
   hdf5_savers.household_saver
   hdf5_savers.leisure_saver
   hdf5_savers.population_saver
   hdf5_savers.school_saver
   hdf5_savers.university_saver


Infection
^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   infection.health_index
   infection.infection
   infection.infection_selector
   infection.symptoms
   infection.symptom_tag
   infection.trajectory_maker
   infection.transmission
   infection.transmission_xnexp


Infection Seed
^^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   infection_seed.infection_seed
   infection_seed.observed_to_cases


Interaction
^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   interaction.interaction
   interaction.interactive_group


Logger
^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   logger.logger
   logger.read_logger
   logger.read_logger_legacy


MPI Setup
^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

    mpi_setup


Paths
^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   paths


Policy
^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   policy.individual_policies
   policy.interaction_policies
   policy.leisure_policies
   policy.medical_care_policies
   policy.policy


Records
^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   records.event_records_writer
   records.records_reader
   records.records_writer
   records.static_records_writer


Simulator Box
^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   simulator_box


Simulator
^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   simulator


Time
^^^^

.. Note: in this case, to avoid a name clash resulting in the Python time
   module (imported by the june module in question) being documented
   instead of june.time, we must specify 'june.time' and then cut off the
   prepended 'june.' (for consistency) with use of a tweaked template.

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   time


Utilities (`utils`)
^^^^^^^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   utils.parse_probabilities
   utils.profiler
   utils.numba_random


World
^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   world
