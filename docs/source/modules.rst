Modules
-------

This lists, and categorises, all modules, where for a given module all
members of that module (classes, functions, etc.) are shown, including
those that are not (yet) documented.


Top-level (`june`) and package `__init__` based modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::
   Most of the modules listed in this particular section just contain
   a package `__init__` with some imports, hence only their names as titles
   will be rendered on the corresponding reference pages.

   However such modules are left in this listing for completeness (note
   also that if any are left out, the Sphinx build will give a warning).


.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june
   june.activity
   june.box
   june.commute
   june.demography
   june.distributors
   june.groups
   june.groups.commute
   june.groups.group
   june.groups.leisure
   june.groups.travel
   june.hdf5_savers
   june.infection
   june.interaction
   june.logger
   june.policy
   june.utils
   

Activity
^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.activity.activity_manager_box
   june.activity.activity_manager


Box
^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.box.box_mode


Commute
^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.commute_rail_travel


Demography
^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.demography.demography
   june.demography.geography
   june.demography.person


Distributors
^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.distributors.carehome_distributor
   june.distributors.company_distributor
   june.distributors.hospital_distributor
   june.distributors.household_distributor
   june.distributors.school_distributor
   june.distributors.university_distributor
   june.distributors.worker_distributor


Exceptions (`exc`)
^^^^^^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.exc


Groups
^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.groups.boundary
   june.groups.carehome
   june.groups.cemetery
   june.groups.company
   june.groups.hospital
   june.groups.household
   june.groups.school
   june.groups.university

See also the sub-sections grouping together related types of `Groups`.


Commute Groups
""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.groups.commute.commutecity_distributor
   june.groups.commute.commutecity
   june.groups.commute.commutecityunit_distributor
   june.groups.commute.commutecityunit
   june.groups.commute.commutehub_distributor
   june.groups.commute.commutehub
   june.groups.commute.commuteunit_distributor
   june.groups.commute.commuteunit

Group Groups
""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.groups.group.abstract
   june.groups.group.group
   june.groups.group.subgroup
   june.groups.group.supergroup


Leisure Groups
""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.groups.leisure.care_home_visits
   june.groups.leisure.cinema
   june.groups.leisure.grocery
   june.groups.leisure.household_visits
   june.groups.leisure.leisure
   june.groups.leisure.pub
   june.groups.leisure.social_venue_distributor
   june.groups.leisure.social_venue


Travel Groups
"""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.groups.travel.travelcity_distributor
   june.groups.travel.travelcity
   june.groups.travel.travelunit_distributor
   june.groups.travel.travelunit


HDF5 Savers
^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.hdf5_savers.carehome_saver
   june.hdf5_savers.commute_saver
   june.hdf5_savers.company_saver
   june.hdf5_savers.geography_saver
   june.hdf5_savers.hospital_saver
   june.hdf5_savers.household_saver
   june.hdf5_savers.leisure_saver
   june.hdf5_savers.population_saver
   june.hdf5_savers.school_saver
   june.hdf5_savers.university_saver


Infection
^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.infection.health_index
   june.infection.health_information
   june.infection.infection
   june.infection_seed.infection_seed
   june.infection_seed.observed_to_cases
   june.infection_seed
   june.infection.symptoms
   june.infection.symptoms_trajectory
   june.infection.symptom_tag
   june.infection.trajectory_maker
   june.infection.transmission
   june.infection.transmission_xnexp


Interaction
^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.interaction.contact_sampling
   june.interaction.interaction
   june.interaction.interactive_group
   june.interaction.matrix_interaction


Logger
^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.logger.logger
   june.logger.read_logger


Paths
^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.paths


Policy
^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.policy.individual_policies
   june.policy.interaction_policies
   june.policy.leisure_policies
   june.policy.medical_care_policies
   june.policy.policy


Simulator Box
^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.simulator_box


Simulator
^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.simulator


Time
^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.time


Utilities (`utils`)
^^^^^^^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.utils.parse_probabilities


Visualization
^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.visualization


World
^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   june.world
