Classes
-------

This lists, and categorises, all classes in `june`, where for a given
class all members of that module are shown, including special, private and
inherited members, and ones that are not (yet) documented.

.. note::
   Note that following the link to view a given class will show it alongside
   the rest of the module it belongs to, so if that module contains multiple
   classes there will be multiple ones on the page. The class in question will
   be highlighted though.


Activity
^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   activity.activity_manager.ActivityManager
   activity.activity_manager_box.ActivityManagerBox


Box
^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   box.box_mode.Box
   box.box_mode.Boxes


Commute
^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   commute.ModeOfTransport
   commute.RegionalGenerator
   commute.CommuteGenerator


Data Formatting
^^^^^^^^^^^^^^^

Include these? (If so, uncomment this section.)

.. .. autosummary::
      :toctree: _autosummary
      :template: class.rst

      data_formatting.google_api.gmapi.APICall
      data_formatting.google_api.gmapi.MSOASearch


Demography
^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   demography.demography.DemographyError
   demography.demography.AgeSexGenerator
   demography.demography.Population
   demography.demography.Demography
   demography.geography.GeographyError
   demography.geography.Area
   demography.geography.Areas
   demography.geography.SuperArea
   demography.geography.SuperAreas
   demography.geography.Geography
   demography.person.Activities
   demography.person.Person


Distributors
^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   distributors.carehome_distributor.CareHomeError
   distributors.carehome_distributor.CareHomeDistributor
   distributors.company_distributor.CompanyDistributor
   distributors.hospital_distributor.HospitalDistributor
   distributors.household_distributor.HouseholdError
   distributors.household_distributor.HouseholdDistributor
   distributors.school_distributor.SchoolDistributor
   distributors.university_distributor.UniversityDistributor
   distributors.worker_distributor.WorkerDistributor


Exceptions (`exc`)
^^^^^^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: exception.rst

   exc.GroupException
   exc.PolicyError
   exc.SimulatorError


Groups
^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   groups.boundary.BoundaryError
   groups.boundary.Boundary
   groups.carehome.CareHomeError
   groups.carehome.CareHome
   groups.carehome.CareHome.SubgroupType
   groups.carehome.CareHomes
   groups.cemetery.Cemetery
   groups.cemetery.Cemeteries
   groups.company.CompanyError
   groups.company.Company
   groups.company.Company.SubgroupType
   groups.company.Companies
   groups.hospital.Hospital
   groups.hospital.Hospital.SubgroupType
   groups.hospital.Hospitals
   groups.household.Household
   groups.household.Household.SubgroupType
   groups.household.Households
   groups.school.SchoolError
   groups.school.School
   groups.school.School.SubgroupType
   groups.school.Schools
   groups.university.University
   groups.university.Universities

See also the sub-sections grouping together related types of `Groups`.


Commute Groups
""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   groups.commute.commutecity.CommuteCity
   groups.commute.commutecity.CommuteCities
   groups.commute.commutecity_distributor.CommuteCityDistributor
   groups.commute.commutecityunit.CommuteCityUnit
   groups.commute.commutecityunit.CommuteCityUnits
   groups.commute.commutecityunit_distributor.CommuteCityUnitDistributor
   groups.commute.commutehub.CommuteHub
   groups.commute.commutehub.CommuteHubs
   groups.commute.commutehub_distributor.CommuteHubDistributor
   groups.commute.commuteunit.CommuteUnit
   groups.commute.commuteunit.CommuteUnits
   groups.commute.commuteunit_distributor.CommuteUnitDistributor


Group Groups
""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   groups.group.abstract.AbstractGroup
   groups.group.group.Group
   groups.group.group.Group.SubgroupType
   groups.group.subgroup.Subgroup
   groups.group.supergroup.Supergroup


Leisure Groups
""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   groups.leisure.care_home_visits.CareHomeVisitsDistributor
   groups.leisure.cinema.Cinema
   groups.leisure.cinema.Cinemas
   groups.leisure.grocery.Grocery
   groups.leisure.grocery.Groceries
   groups.leisure.grocery.GroceryDistributor
   groups.leisure.household_visits.HouseholdVisitsDistributor
   groups.leisure.leisure.Leisure
   groups.leisure.pub.Pub
   groups.leisure.pub.Pubs
   groups.leisure.pub.PubDistributor
   groups.leisure.social_venue_distributor.SocialVenueDistributor
   groups.leisure.social_venue.SocialVenueError
   groups.leisure.social_venue.SocialVenue
   groups.leisure.social_venue.SocialVenue.SubgroupType
   groups.leisure.social_venue.SocialVenues


Travel Groups
"""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   groups.travel.travelcity_distributor.TravelCityDistributor
   groups.travel.travelcity.TravelCity
   groups.travel.travelcity.TravelCities
   groups.travel.travelunit_distributor.TravelUnitDistributor
   groups.travel.travelunit.TravelUnit
   groups.travel.travelunit.TravelUnits


Infection
^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   infection.health_index.HealthIndexGenerator
   infection.health_information.HealthInformation
   infection.infection.SymptomsType
   infection.infection.InfectionSelector
   infection.infection.Infection
   infection_seed.infection_seed.InfectionSeed
   infection_seed.observed_to_cases.Observed2Cases
   infection.symptoms.Symptoms
   infection.symptom_tag.SymptomTag
   infection.trajectory_maker.CompletionTime
   infection.trajectory_maker.ConstantCompletionTime
   infection.trajectory_maker.DistributionCompletionTime
   infection.trajectory_maker.ExponentialCompletionTime
   infection.trajectory_maker.BetaCompletionTime
   infection.trajectory_maker.LognormalCompletionTime
   infection.trajectory_maker.NormalCompletionTime
   infection.trajectory_maker.ExponweibCompletionTime
   infection.trajectory_maker.Stage
   infection.trajectory_maker.TrajectoryMaker
   infection.trajectory_maker.TrajectoryMakers
   infection.transmission.Transmission
   infection.transmission.TransmissionConstant
   infection.transmission.TransmissionGamma
   infection.transmission_xnexp.TransmissionXNExp


Interaction
^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   interaction.contact_sampling.ContactSampling
   interaction.interaction.Interaction
   interaction.interactive_group.InteractiveGroup
   interaction.matrix_interaction.MatrixInteraction


Logger
^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   logger.logger.Logger
   logger.read_logger.ReadLogger


Policy
^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   policy.individual_policies.IndividualPolicy
   policy.individual_policies.IndividualPolicies
   policy.individual_policies.StayHome
   policy.individual_policies.SevereSymptomsStayHome
   policy.individual_policies.Quarantine
   policy.individual_policies.Shielding
   policy.individual_policies.SkipActivity
   policy.individual_policies.CloseSchools
   policy.individual_policies.CloseUniversities
   policy.individual_policies.CloseCompanies
   policy.interaction_policies.InteractionPolicy
   policy.interaction_policies.InteractionPolicies
   policy.interaction_policies.SocialDistancing
   policy.interaction_policies.MaskWearing
   policy.leisure_policies.LeisurePolicy
   policy.leisure_policies.LeisurePolicies
   policy.leisure_policies.CloseLeisureVenue
   policy.leisure_policies.ChangeLeisureProbability
   policy.medical_care_policies.MedicalCarePolicy
   policy.medical_care_policies.MedicalCarePolicies
   policy.medical_care_policies.Hospitalisation
   policy.policy.Policy
   policy.policy.Policies
   policy.policy.PolicyCollection


Simulator Box
^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   simulator_box.SimulatorError
   simulator_box.SimulatorBox


Simulator
^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   simulator.Simulator


Time
^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   .. time.Timer


.. Visualization
   ^^^^^^^^^^^^^

   Note that 'visualization.plotter.DashPlotter' has been omitted since it
   has not been added to the june namespace so can't be imported to be
   processed like the other items here by the Sphinx autosummary extension.


World
^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   world.World
