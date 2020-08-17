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

   june.activity.activity_manager.ActivityManager
   june.activity.activity_manager_box.ActivityManagerBox


Box
^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.box.box_mode.Box
   june.box.box_mode.Boxes


Commute
^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.commute.ModeOfTransport
   june.commute.RegionalGenerator
   june.commute.CommuteGenerator


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

   june.demography.demography.DemographyError
   june.demography.demography.AgeSexGenerator
   june.demography.demography.Population
   june.demography.demography.Demography
   june.demography.geography.GeographyError
   june.demography.geography.Area
   june.demography.geography.Areas
   june.demography.geography.SuperArea
   june.demography.geography.SuperAreas
   june.demography.geography.Geography
   june.demography.person.Activities
   june.demography.person.Person


Distributors
^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.distributors.carehome_distributor.CareHomeError
   june.distributors.carehome_distributor.CareHomeDistributor
   june.distributors.company_distributor.CompanyDistributor
   june.distributors.hospital_distributor.HospitalDistributor
   june.distributors.household_distributor.HouseholdError
   june.distributors.household_distributor.HouseholdDistributor
   june.distributors.school_distributor.SchoolDistributor
   june.distributors.university_distributor.UniversityDistributor
   june.distributors.worker_distributor.WorkerDistributor


Exceptions (`exc`)
^^^^^^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.exc.GroupException
   june.exc.PolicyError
   june.exc.SimulatorError


Groups
^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.groups.boundary.BoundaryError
   june.groups.boundary.Boundary
   june.groups.carehome.CareHomeError
   june.groups.carehome.CareHome
   june.groups.carehome.SubgroupType
   june.groups.carehome.CareHomes
   june.groups.cemetery.Cemetery
   june.groups.cemetery.Cemeteries
   june.groups.company.CompanyError
   june.groups.company.Company
   june.groups.company.SubgroupType
   june.groups.company.Companies
   june.groups.hospital.Hospital
   june.groups.hospital.SubgroupType
   june.groups.hospital.Hospitals
   june.groups.household.Household
   june.groups.household.SubgroupType
   june.groups.household.Households
   june.groups.school.SchoolError
   june.groups.school.School
   june.groups.school.SubgroupType
   june.groups.school.Schools
   june.groups.university.University
   june.groups.university.Universities

See also the sub-sections grouping together related types of `Groups`.


Commute Groups
""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.groups.commute.commutecity.CommuteCity
   june.groups.commute.commutecity.CommuteCities
   june.groups.commute.commutecity_distributor.CommuteCityDistributor
   june.groups.commute.commutecityunit.CommuteCityUnit
   june.groups.commute.commutecityunit.CommuteCityUnits
   june.groups.commute.commutecityunit_distributor.CommuteCityUnitDistributor
   june.groups.commute.commutehub.CommuteHub
   june.groups.commute.commutehub.CommuteHubs
   june.groups.commute.commutehub_distributor.CommuteHubDistributor
   june.groups.commute.commuteunit.CommuteUnit
   june.groups.commute.commuteunit.CommuteUnits
   june.groups.commute.commuteunit_distributor.CommuteUnitDistributor


Group Groups
""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.groups.group.abstract.AbstractGroup
   june.groups.group.group.Group
   june.groups.group.group.SubgroupType
   june.groups.group.subgroup.Subgroup
   june.groups.group.supergroup.Supergroup


Leisure Groups
""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.groups.leisure.care_home_visits.CareHomeVisitsDistributor
   june.groups.leisure.cinema.Cinema
   june.groups.leisure.cinema.Cinemas
   june.groups.leisure.grocery.Grocery
   june.groups.leisure.grocery.Groceries
   june.groups.leisure.grocery.GroceryDistributor
   june.groups.leisure.household_visits.HouseholdVisitsDistributor
   june.groups.leisure.leisure.Leisure
   june.groups.leisure.pub.Pub
   june.groups.leisure.pub.Pubs
   june.groups.leisure.pub.PubDistributor
   june.groups.leisure.social_venue_distributor.SocialVenueDistributor
   june.groups.leisure.social_venue.SocialVenueError
   june.groups.leisure.social_venue.SocialVenue
   june.groups.leisure.social_venue.SubgroupType
   june.groups.leisure.social_venue.SocialVenues


Travel Groups
"""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.groups.travel.travelcity_distributor.TravelCityDistributor
   june.groups.travel.travelcity.TravelCity
   june.groups.travel.travelcity.TravelCities
   june.groups.travel.travelunit_distributor.TravelUnitDistributor
   june.groups.travel.travelunit.TravelUnit
   june.groups.travel.travelunit.TravelUnits


Infection
^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.infection.health_index.HealthIndexGenerator
   june.infection.health_information.HealthInformation
   june.infection.infection.SymptomsType
   june.infection.infection.InfectionSelector
   june.infection.infection.Infection
   june.infection_seed.infection_seed.InfectionSeed
   june.infection_seed.observed_to_cases.Observed2Cases
   june.infection.symptoms.Symptoms
   june.infection.symptom_tag.SymptomTag
   june.infection.trajectory_maker.CompletionTime
   june.infection.trajectory_maker.ConstantCompletionTime
   june.infection.trajectory_maker.DistributionCompletionTime
   june.infection.trajectory_maker.ExponentialCompletionTime
   june.infection.trajectory_maker.BetaCompletionTime
   june.infection.trajectory_maker.LognormalCompletionTime
   june.infection.trajectory_maker.NormalCompletionTime
   june.infection.trajectory_maker.ExponweibCompletionTime
   june.infection.trajectory_maker.Stage
   june.infection.trajectory_maker.TrajectoryMaker
   june.infection.trajectory_maker.TrajectoryMakers
   june.infection.transmission.Transmission
   june.infection.transmission.TransmissionConstant
   june.infection.transmission.TransmissionGamma
   june.infection.transmission_xnexp.TransmissionXNExp


Interaction
^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.interaction.contact_sampling.ContactSampling
   june.interaction.interaction.Interaction
   june.interaction.interactive_group.InteractiveGroup
   june.interaction.matrix_interaction.MatrixInteraction


Logger
^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.logger.logger.Logger
   june.logger.read_logger.ReadLogger


Policy
^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.policy.individual_policies.IndividualPolicy
   june.policy.individual_policies.IndividualPolicies
   june.policy.individual_policies.StayHome
   june.policy.individual_policies.SevereSymptomsStayHome
   june.policy.individual_policies.Quarantine
   june.policy.individual_policies.Shielding
   june.policy.individual_policies.SkipActivity
   june.policy.individual_policies.CloseSchools
   june.policy.individual_policies.CloseUniversities
   june.policy.individual_policies.CloseCompanies
   june.policy.interaction_policies.InteractionPolicy
   june.policy.interaction_policies.InteractionPolicies
   june.policy.interaction_policies.SocialDistancing
   june.policy.interaction_policies.MaskWearing
   june.policy.leisure_policies.LeisurePolicy
   june.policy.leisure_policies.LeisurePolicies
   june.policy.leisure_policies.CloseLeisureVenue
   june.policy.leisure_policies.ChangeLeisureProbability
   june.policy.medical_care_policies.MedicalCarePolicy
   june.policy.medical_care_policies.MedicalCarePolicies
   june.policy.medical_care_policies.Hospitalisation
   june.policy.policy.Policy
   june.policy.policy.Policies
   june.policy.policy.PolicyCollection


Simulator Box
^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.simulator_box.SimulatorError
   june.simulator_box.SimulatorBox


Simulator
^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.simulator.Simulator


Time
^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.time.Timer


Visualization
^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.visualization.plotter.DashPlotter


World
^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   june.world.World
