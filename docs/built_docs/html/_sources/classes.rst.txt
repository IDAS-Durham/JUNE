.. Note: it is important to keep the current module setting below in
   this file because it prevents any nameclashes with any imports, e.g.
   'june.time' vs. Python's in-built 'time', which otherwise would be
   documented instead.

.. currentmodule:: june


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


.. Data Formatting
   ^^^^^^^^^^^^^^^

   Note that:
       data_formatting.google_api.gmapi.APICall
       data_formatting.google_api.gmapi.MSOASearch
   have been omitted since they are not in the june namespace so can't be
   imported to be processed by the Sphinx autosummary extension.


Demography
^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   demography.demography.AgeSexGenerator
   demography.demography.Population
   demography.demography.Demography
   demography.demography.ComorbidityGenerator
   demography.person.Activities
   demography.person.Person


Exceptions (Exception classes):

.. autosummary::
   :toctree: _autosummary
   :template: exceptions.rst

   demography.demography.DemographyError


Distributors
^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   distributors.care_home_distributor.CareHomeDistributor
   distributors.company_distributor.CompanyDistributor
   distributors.hospital_distributor.HospitalDistributor
   distributors.household_distributor.HouseholdDistributor
   distributors.school_distributor.SchoolDistributor
   distributors.university_distributor.UniversityDistributor
   distributors.worker_distributor.WorkerDistributor


Exceptions (Exception classes):

.. autosummary::
   :toctree: _autosummary
   :template: exceptions.rst

   distributors.care_home_distributor.CareHomeError
   distributors.household_distributor.HouseholdError


Domain
^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   domain.Domain
   domain.DomainSplitter


Exceptions (`exc`)
^^^^^^^^^^^^^^^^^^

Exceptions (Exception classes):

.. autosummary::
   :toctree: _autosummary
   :template: exception.rst

   exc.GroupException
   exc.PolicyError
   exc.HospitalError
   exc.SimulatorError
   exc.InteractionError


Geography
^^^^^^^^^

City
""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   geography.city.City
   geography.city.Cities
   geography.city.ExternalCity


Geography
"""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   geography.geography.Area
   geography.geography.Areas
   geography.geography.SuperArea
   geography.geography.SuperAreas
   geography.geography.ExternalSuperArea
   geography.geography.Region
   geography.geography.Regions
   geography.geography.Geography


Exceptions (Exception classes):

.. autosummary::
   :toctree: _autosummary
   :template: exceptions.rst

   geography.geography.GeographyError


Station
"""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   geography.station.Station
   geography.station.Stations
   geography.station.ExternalStation


Groups
^^^^^^

Group Groups
""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   groups.group.abstract.AbstractGroup
   groups.group.external.ExternalGroup
   groups.group.external.ExternalSubgroup
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
   groups.leisure.social_venue.SocialVenue
   groups.leisure.social_venue.SocialVenue.SubgroupType
   groups.leisure.social_venue.SocialVenues


Exceptions (Exception classes):

.. autosummary::
   :toctree: _autosummary
   :template: exceptions.rst

   groups.leisure.social_venue.SocialVenueError


Travel Groups
"""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   groups.travel
   groups.travel.mode_of_transport.ModeOfTransport
   groups.travel.mode_of_transport.RegionalGenerator
   groups.travel.mode_of_transport.ModeOfTransportGenerator
   groups.travel.transport.Transport
   groups.travel.transport.Transport.SubgroupType
   groups.travel.transport.Transports
   groups.travel.transport.CityTransport
   groups.travel.transport.CityTransports
   groups.travel.transport.InterCityTransport
   groups.travel.transport.InterCityTransports
   groups.travel.transport.InterRegionalTransport
   groups.travel.transport.InterRegionalTransports
   groups.travel.travel.Travel


.. Travel Groups (*Old*)
   """""""""""""""""""""

   .. groups.travel_old.commute_old.Commute
   .. groups.travel_old.commute_old.commutecity.CommuteCity
   .. groups.travel_old.commute_old.commutecity.CommuteCities
   .. groups.travel_old.commute_old.commutecity_distributor.CommuteCityDistributor
   .. groups.travel_old.commute_old.commutecityunit.CommuteCityUnit
   .. groups.travel_old.commute_old.commutecityunit.CommuteCityUnits
   .. groups.travel_old.commute_old.commutecityunit.CommuteCityUnits
   .. groups.travel_old.commute_old.commutecityunit_distributor.CommuteCityUnitDistributor
   .. groups.travel_old.commute_old.commutehub.CommuteHub
   .. groups.travel_old.commute_old.commutehub.CommuteHubs
   .. groups.travel_old.commute_old.commutehub_distributor.CommuteHubDistributor
   .. groups.travel_old.commute_old.commuteunit.CommuteUnit
   .. groups.travel_old.commute_old.commuteunit.CommuteUnits
   .. groups.travel_old.commute_old.commuteunit_distributor.CommuteUnitDistributor
   .. groups.travel_old.travelcity.TravelCity
   .. groups.travel_old.travelcity.TravelCities
   .. groups.travel_old.travelcity_distributor.TravelCityDistributor
   .. groups.travel_old.travelunit.TravelUnit
   .. groups.travel_old.travelunit.TravelUnits
   .. groups.travel_old.travelunit_distributor.TravelUnitDistributor


.. Exceptions (Exception classes):

   .. groups.travel_old.commute_old.commutecity.CommuteError


.. Commute Groups
   """"""""""""""

   .. groups.commute.commutecity.CommuteCity
   .. groups.commute.commutecity.CommuteCities
   .. groups.commute.commutehub.CommuteHub
   .. groups.commute.commutehub.CommuteHubs
   .. groups.commute.commutehub_distributor.CommuteHubDistributor


   Exceptions (Exception classes):

   .. groups.commute.commutecity.CommuteError

Other Groups
""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   groups.boundary.Boundary
   groups.care_home.CareHome
   groups.care_home.CareHome.SubgroupType
   groups.care_home.CareHomes
   groups.cemetery.Cemetery
   groups.cemetery.Cemeteries
   groups.company.Company
   groups.company.Company.SubgroupType
   groups.company.Companies
   groups.hospital.AbstractHospital
   groups.hospital.Hospital
   groups.hospital.Hospital.SubgroupType
   groups.hospital.Hospitals
   groups.hospital.ExternalHospital
   groups.household.Household
   groups.household.Household.SubgroupType
   groups.household.Households
   groups.school.School
   groups.school.School.SubgroupType
   groups.school.Schools
   groups.university.University
   groups.university.Universities


Exceptions (Exception classes):

.. autosummary::
   :toctree: _autosummary
   :template: exceptions.rst

   groups.boundary.BoundaryError
   groups.care_home.CareHomeError
   groups.company.CompanyError
   groups.school.SchoolError


Infection
^^^^^^^^^

Infection Trajectory Maker
""""""""""""""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

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


Infection Transmission (including `XNExp`)
""""""""""""""""""""""""""""""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   infection.transmission.Transmission
   infection.transmission.TransmissionConstant
   infection.transmission.TransmissionGamma
   infection.transmission_xnexp.TransmissionXNExp


Other Infection
"""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   infection.infection.Infection
   infection.infection_selector.InfectionSelector
   infection.health_index.HealthIndexGenerator
   infection.symptom_tag.SymptomTag
   infection.symptoms.Symptoms


Infection Seed
^^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   infection_seed.infection_seed.InfectionSeed
   infection_seed.observed_to_cases.Observed2Cases


Interaction
^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   interaction.interaction.Interaction
   interaction.interactive_group.InteractiveGroup


Logger
^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   logger.logger.Logger
   logger.read_logger.ReadLogger
   logger.read_logger_legacy.ReadLoggerLegacy


MPI Setup
^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

    mpi_setup.MovablePeople


Policy
^^^^^^

Individual Policies
"""""""""""""""""""

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


Interaction Policies
""""""""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   policy.interaction_policies.InteractionPolicy
   policy.interaction_policies.InteractionPolicies
   policy.interaction_policies.SocialDistancing
   policy.interaction_policies.MaskWearing


Leisure Policies
""""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   policy.leisure_policies.LeisurePolicy
   policy.leisure_policies.LeisurePolicies
   policy.leisure_policies.CloseLeisureVenue
   policy.leisure_policies.ChangeLeisureProbability


Medical Care Policies
"""""""""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   policy.medical_care_policies.MedicalCarePolicy
   policy.medical_care_policies.MedicalCarePolicies
   policy.medical_care_policies.Hospitalisation


(Policy) Policy
"""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   policy.policy.Policy
   policy.policy.Policies
   policy.policy.PolicyCollection


Records
^^^^^^^

Event Records Writer
""""""""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   records.event_records_writer.EventRecord
   records.event_records_writer.InfectionRecord
   records.event_records_writer.HospitalAdmissionsRecord
   records.event_records_writer.ICUAdmissionsRecord
   records.event_records_writer.DischargesRecord
   records.event_records_writer.DeathsRecord
   records.event_records_writer.RecoveriesRecord
   records.event_records_writer.SymptomsRecord


Static Records Writer
"""""""""""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   records.static_records_writer.StaticRecord
   records.static_records_writer.PeopleRecord
   records.static_records_writer.LocationRecord
   records.static_records_writer.AreaRecord
   records.static_records_writer.SuperAreaRecord
   records.static_records_writer.RegionRecord


Other Records
"""""""""""""

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   records.records_reader.RecordReader
   records.records_writer.Record


Simulator Box
^^^^^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   simulator_box.SimulatorBox


Exceptions (Exception classes):

.. autosummary::
   :toctree: _autosummary
   :template: exceptions.rst

   simulator_box.SimulatorError


Simulator
^^^^^^^^^

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   simulator.Simulator


Time
^^^^

.. Note: in this case, to avoid a name clash resulting in the Python time
   module (imported by the june module in question) being documented
   instead of june.time, we must specify 'june.time' and then cut off the
   prepended 'june.' (for consistency) with use of a tweaked template.

.. autosummary::
   :toctree: _autosummary
   :template: class.rst

   time.Timer


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
