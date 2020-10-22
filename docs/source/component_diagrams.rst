Component diagrams
------------------

.. Docs note 1: it does not seem to be possible to use an autosummary
   template to apply the same ''uml' directive to all components below.
   However, it is not much more work to just use the 'uml' directive
   directly for each.

.. Docs note 2: there are some further JUNE modules such as 'Records'
   which are not included here, either because when generated they are
   blank (empty) diagrams due to having no class or module structure,
   or because attempts to add them here in the same way
   as the other modules lead to errors in generation of the diagrams
   ultimately coming through as an error breaking the Sphinx build, e.g:

   Exception occurred:
     File "/home/sadie/anaconda3/envs/june/lib/python3.8/site-packages/PIL/Image.py", line 2878, in open
     fp = builtins.open(filename, "rb")
     FileNotFoundError: [Errno 2] No such file or directory: '/home/sadie/JUNE/docs/source/uml_images/packages_june.record.png'

   These might get fixed in a newer version of sphinx_pyreverse, pyreverse
   or Sphinx. Or there may be some reason based on the code structure or
   nature that those diagrams can't be generated. I do not have time to
   investigate, but it might be fixable.


Activity
^^^^^^^^

Classes
"""""""

.. uml:: june.activity
    :classes:


Modules
"""""""

.. uml:: june.activity
    :packages:
       

Box
^^^

Classes
"""""""

.. uml:: june.box
    :classes:


Modules
"""""""

.. uml:: june.box
    :packages:


Demography
^^^^^^^^^^

Classes
"""""""

.. uml:: june.demography
    :classes:


Modules
"""""""

.. uml:: june.demography
    :packages:


Distributors
^^^^^^^^^^^^

Classes
"""""""

.. uml:: june.distributors
    :classes:


Modules
"""""""

.. uml:: june.distributors
    :packages:


Geography
^^^^^^^^^

Classes
"""""""

.. uml:: june.geography
    :classes:


Modules
"""""""

.. uml:: june.geography
    :packages:


Groups
^^^^^^

Classes
"""""""

.. uml:: june.groups
    :classes:


Modules
"""""""

.. uml:: june.groups
    :packages:

See also the sub-sections below, showing sub-diagrams for the various
types of `Groups`.


Commute Groups
""""""""""""""

Classes
"""""""

.. uml:: june.groups.commute
    :classes:


Modules
"""""""

.. uml:: june.groups.commute
    :packages:


Group Groups
""""""""""""

Classes
"""""""

.. uml:: june.groups.group
    :classes:


Modules
"""""""

.. uml:: june.groups.group
    :packages:


Leisure Groups
""""""""""""""

Classes
"""""""

.. uml:: june.groups.leisure
    :classes:


Modules
"""""""

.. uml:: june.groups.leisure
    :packages:


Travel Groups
"""""""""""""

Classes
"""""""

.. uml:: june.groups.travel
    :classes:


Modules
"""""""

.. uml:: june.groups.travel
    :packages:


HDF5 Savers
^^^^^^^^^^^

Modules
"""""""

.. uml:: june.hdf5_savers
    :packages:


Infection
^^^^^^^^^

Classes
"""""""

.. uml:: june.infection
    :classes:


Modules
"""""""

.. uml:: june.infection
    :packages:


Infection Seed
^^^^^^^^^^^^^^

Classes
"""""""

.. uml:: june.infection_seed
    :classes:


Modules
"""""""

.. uml:: june.infection_seed
    :packages:


Interaction
^^^^^^^^^^^

Classes
"""""""

.. uml:: june.interaction
    :classes:


Modules
"""""""

.. uml:: june.interaction
    :packages:


Logger
^^^^^^

Classes
"""""""

.. uml:: june.logger
    :classes:


Modules
"""""""

.. uml:: june.logger
    :packages:


Policy
^^^^^^

Classes
"""""""

.. uml:: june.policy
    :classes:


Modules
"""""""

.. uml:: june.policy
    :packages:


Utilities (`utils`)
^^^^^^^^^^^^^^^^^^^

Modules
"""""""

.. uml:: june.utils
    :packages:


Visualization
^^^^^^^^^^^^^

Classes
"""""""

.. uml:: june.visualization
    :classes:


Modules
"""""""

.. uml:: june.visualization
    :packages:
