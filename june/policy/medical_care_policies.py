import datetime
import logging
from typing import List, Optional, Any, Set, Union
import logging
import random
import inspect
import functools
from june.epidemiology.test_and_trace import TestAndTrace

from june.epidemiology.infection.disease_config import DiseaseConfig
from june.global_context import GlobalContext
from june.records.event_recording import emit_test_event, emit_trace_event
from .policy import Policy, PolicyCollection
from june.demography import Person
from june.records import Record
from june.mpi_wrapper import MPI, mpi_rank

# Global signature cache to prevent repeated inspection calls
@functools.lru_cache(maxsize=256)
def get_cached_signature_params(func):
    return inspect.signature(func).parameters


class MedicalCarePolicy(Policy):
    """Base class for all medical care policies with standardized configuration"""
    
    def __init__(self, start_time: Union[str, datetime.datetime] , end_time:Union[str, datetime.datetime], disease_config: DiseaseConfig = None):

        super().__init__(start_time=start_time, end_time=end_time)
        self.policy_type = "medical_care"
        self.disease_config = disease_config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Load policy-specific configuration if disease_config is provided
        if disease_config:
            self._load_policy_config()
        
    def _load_policy_config(self):
        """Load policy configuration from disease_config"""
        # Default implementation, to be overridden by subclasses
        policy_name = self.__class__.__name__.lower()
        try:
            if self.disease_config and hasattr(self.disease_config, "policy_manager"):
                policy_data = self.disease_config.policy_manager.get_policy_data(policy_name)
                if policy_data:
                    for key, value in policy_data.items():
                        setattr(self, key, value)
                    self.logger.debug(f"Loaded configuration for {policy_name}: {policy_data}")
        except Exception as e:
            self.logger.warning(f"Error loading configuration for {policy_name}: {e}")

    def is_active(self, date: datetime.datetime) -> bool:
        """
        Check if policy is active on the given date.
        This implementation handles type mismatches by converting as needed.
        """
        # Convert date to date if comparing with date
        if isinstance(self.start_time, datetime.date) and not isinstance(self.start_time, datetime.datetime):
            date_for_comparison = date.date() if isinstance(date, datetime.datetime) else date
            return self.start_time <= date_for_comparison < self.end_time
        
        # Convert start_time and end_time to datetime if comparing with datetime
        elif isinstance(date, datetime.datetime) and not isinstance(self.start_time, datetime.datetime):
            start_datetime = datetime.datetime.combine(self.start_time, datetime.time.min)
            end_datetime = datetime.datetime.combine(self.end_time, datetime.time.min)
            return start_datetime <= date < end_datetime
        
        # Normal case - types match
        else:
            return self.start_time <= date < self.end_time
    
        
    def apply(self, 
              person: Person, 
              days_from_start: float = None, 
              record: Optional[Record] = None, 
              simulator = None) -> bool:
        """
        Apply the policy to a person.
        
        Parameters
        ----------
        person : Person
            The person to whom the policy is applied
        days_from_start : float, optional
            Days since the start of the simulation
        record : Record, optional
            Record object for logging
        simulator : object, optional
            Simulator object for additional context
            
        Returns
        -------
        bool
            True if the policy was applied and should stop the chain, False otherwise
        """
        raise NotImplementedError("Subclasses must implement apply method")


class PolicyChain:
    """
    Represents a chain of policies that should be applied sequentially.
    If a policy in the chain activates, subsequent policies in the chain
    are applied if they exist and are configured to continue the chain.
    """
    
    def __init__(self, 
                 starting_policies: List[MedicalCarePolicy],
                 next_chain: Optional['PolicyChain'] = None,
                 requires_activation: bool = True):
        """
        Initialize a policy chain.
        
        Parameters
        ----------
        starting_policies : List[MedicalCarePolicy]
            The policies to apply at the start of this chain
        next_chain : PolicyChain, optional
            The next chain to apply if this chain activates
        requires_activation : bool
            If True, the next chain is only applied if a policy in this chain activates
        """
        self.starting_policies = starting_policies
        self.next_chain = next_chain
        self.requires_activation = requires_activation
        
        # Debug flag - set to False by default
        self.debug = False
        
    def apply(self, **kwargs) -> bool:
        """
        Apply this policy chain.
        
        Returns
        -------
        bool
            True if any policy in the chain was activated, False otherwise.
        """
        chain_activated = False
        
        # Apply each starting policy
        for policy in self.starting_policies:
            try:
                # Use the global cached signature function instead of computing it each time
                policy_apply_params = get_cached_signature_params(policy.apply)
                expected_kwargs = {k: v for k, v in kwargs.items() if k in policy_apply_params}
                
                # Apply the policy (no need to check is_active since we're using pre-filtered active policies)
                policy_activated = policy.apply(**expected_kwargs)
                chain_activated = chain_activated or policy_activated
                
                if policy_activated and self.debug:
                    print(f"Policy {policy.__class__.__name__} was activated")
                    
            except Exception as e:
                logging.error(f"Error applying policy {policy.__class__.__name__}: {e}")
                import traceback
                logging.error(traceback.format_exc())
        
        # Apply the next chain if it exists and conditions are met
        if self.next_chain and (not self.requires_activation or chain_activated):
            next_chain_activated = self.next_chain.apply(**kwargs)
            chain_activated = chain_activated or next_chain_activated
        
        return chain_activated


class MedicalCarePolicies(PolicyCollection):
    policy_type = "medical_care"
    
    # Class-level cache for active policies by date
    _active_policies_cache = {}
    # Maximum cache size to prevent memory issues
    _max_cache_size = 100

    def __init__(self, policies: List[Policy]):
        """
        A collection of like policies active on the same date with flexible chaining
        """
        super().__init__(policies)

        # Standard categorization of policies (for backward compatibility)
        self.hospitalisation_policies = [
            policy for policy in self.policies if isinstance(policy, Hospitalisation)
        ]
        self.testing_policies = [
            policy for policy in self.policies if isinstance(policy, Testing)
        ]
        self.tracing_policies = [
            policy for policy in self.policies if isinstance(policy, Tracing)
        ]
        self.non_hospitalisation_policies = [
            policy
            for policy in self.policies
            if not isinstance(policy, (Hospitalisation, Testing, Tracing))
        ]
        
        # Set up policy chains
        self._setup_policy_chains()
        
    def _setup_policy_chains(self):
        """Configure policy chains based on dependencies"""

        self.policy_chains = []
        
        # Create the hospitalization → testing → tracing chain
        if self.hospitalisation_policies:
            # Start with hospitalization
            hospitalisation_chain = PolicyChain(
                starting_policies=self.hospitalisation_policies
            )
            
            # Add testing as the next step
            if self.testing_policies:
                testing_chain = PolicyChain(
                    starting_policies=self.testing_policies,
                    requires_activation=True  # Only test if hospitalization activated
                )
                hospitalisation_chain.next_chain = testing_chain
                
                # Add tracing as the final step
                if self.tracing_policies:
                    tracing_chain = PolicyChain(
                        starting_policies=self.tracing_policies,
                        requires_activation=True  # Only trace if testing activated with positive result
                    )
                    testing_chain.next_chain = tracing_chain
            
            # Add the full chain to the policy chains
            self.policy_chains.append(hospitalisation_chain)
        
        # Add other non-hospitalization policies as separate chains
        for policy in self.non_hospitalisation_policies:
            self.policy_chains.append(
                PolicyChain(starting_policies=[policy])
            )
    
    def get_active(self, date: datetime.datetime):
        # Use caching for faster lookups
        if isinstance(date, datetime.datetime):
            cache_key = date.toordinal() * 24 + date.hour
        else:
            # Handle date objects by converting to days since epoch
            cache_key = date.toordinal()
            
        if cache_key in self._active_policies_cache:
            return self._active_policies_cache[cache_key]
        
        # Get all active policies regardless of type first
        all_policies = [self.hospitalisation_policies, self.testing_policies, self.tracing_policies]
        active_policies = [
            policy for policy_collection in all_policies 
            for policy in policy_collection 
            if policy.is_active(date)
        ]
        
        
        simulator = GlobalContext.get_simulator()
        test_and_trace_enabled = simulator.test_and_trace_enabled
        
        # If test and trace is disabled, filter out testing and tracing policies
        if not test_and_trace_enabled:
            filtered_policies = [
                policy for policy in active_policies
                if not isinstance(policy, (Testing, Tracing))
            ]
            result = MedicalCarePolicies(filtered_policies)
        else:
            result = MedicalCarePolicies(active_policies)
        
        # Cache the result
        self._active_policies_cache[cache_key] = result
        
        # Limit cache size to prevent memory leaks
        if len(self._active_policies_cache) > self._max_cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self._active_policies_cache))
            del self._active_policies_cache[oldest_key]
        
        return result

    def apply(
        self,
        person: Person,
        disease_config: DiseaseConfig,
        medical_facilities,
        days_from_start: float,
        record: Optional[Record],
        simulator = None,
        active_medical_care_policies = None
    ) -> None:
        """
        Applies medical care policies using the policy chain pattern.
        
        Parameters
        ----------
        person : Person
            The person to apply policies to
        disease_config : DiseaseConfig
            The disease configuration
        medical_facilities
            Medical facilities available for allocation
        days_from_start : float
            Days since the start of the simulation
        record : Record
            Record object for logging
        simulator : object
            Simulator object for additional context
        active_medical_care_policies : MedicalCarePolicies, optional
            Pre-filtered active policies, to avoid redundant active policy checks
        """
        try:
            # Use pre-filtered active policies if provided
            if active_medical_care_policies is not None:
                # Create policy chains with only the active policies
                policy_chains = []
                
                # Create active hospitalization chain
                active_hospitalisation_policies = [
                    policy for policy in active_medical_care_policies.hospitalisation_policies
                ]
                if active_hospitalisation_policies:
                    hospitalisation_chain = PolicyChain(
                        starting_policies=active_hospitalisation_policies
                    )
                    
                    # Add active testing policies
                    active_testing_policies = [
                        policy for policy in active_medical_care_policies.testing_policies
                    ]
                    if active_testing_policies:
                        testing_chain = PolicyChain(
                            starting_policies=active_testing_policies,
                            requires_activation=True
                        )
                        hospitalisation_chain.next_chain = testing_chain
                        
                        # Add active tracing policies
                        active_tracing_policies = [
                            policy for policy in active_medical_care_policies.tracing_policies
                        ]
                        if active_tracing_policies:
                            tracing_chain = PolicyChain(
                                starting_policies=active_tracing_policies,
                                requires_activation=True
                            )
                            testing_chain.next_chain = tracing_chain
                    
                    policy_chains.append(hospitalisation_chain)
                    
                # Add active non-hospitalization policies
                active_non_hosp_policies = [
                    policy for policy in active_medical_care_policies.non_hospitalisation_policies
                ]
                for policy in active_non_hosp_policies:
                    policy_chains.append(PolicyChain(starting_policies=[policy]))
                    
                # Apply each active policy chain
                for chain in policy_chains:
                    # The policies are already known to be active, so we can skip the is_active check
                    # when applying them in the PolicyChain
                    chain_activated = chain.apply(
                        person=person,
                        days_from_start=days_from_start,
                        record=record,
                        simulator=simulator
                    )
                    
                    # If a chain was activated, stop processing
                    if chain_activated:
                        return
                    
        except Exception as e:
            logging.error(f"Error in medical care policy application: {e}")
            import traceback
            logging.error(traceback.format_exc())


class Hospitalisation(MedicalCarePolicy):
    """
    Hospitalisation policy. When applied to a sick person, allocates that person to a hospital, if the symptoms are severe
    enough. When the person recovers, releases the person from the hospital.
    """

    def __init__(
        self, 
        disease_config: DiseaseConfig, 
        start_time: Union[str, datetime.datetime] = "1900-01-01",
        end_time: Union[str, datetime.datetime] = "2100-01-01",
    ):
        """
        Initialize the hospitalisation policy.

        Parameters
        ----------
        disease_config : DiseaseConfig
            Configuration object for the disease.
        start_time : str
            Start time for the policy.
        end_time : str
            End time for the policy.
        """
        if disease_config is None:
            raise ValueError("disease_config must be provided for Hospitalisation policy.")
        
        super().__init__(start_time, end_time, disease_config)
        self.debug = False

    def _load_policy_config(self):
        """Load hospitalisation-specific configuration"""
        super()._load_policy_config()

    def apply(self, person: Person, days_from_start: float = None, record: Optional[Record] = None, simulator = None) -> bool:
        """
        Apply the hospitalisation policy to a person.

        Parameters
        ----------
        person : Person
            The person to whom the policy is applied.
        days_from_start : float
            Days since the start of the simulation.
        record : Optional[Record]
            The record for logging events.
        simulator : object
            Simulator object for additional context.

        Returns
        -------
        bool
            True if the person was hospitalised or discharged, False otherwise.
        """
        # Retrieve relevant stages from the disease configuration
        hospitalised_tags = set(self.disease_config.symptom_manager._resolve_tags("hospitalised_stage"))
        dead_hospital_tags = set(self.disease_config.symptom_manager._resolve_tags("fatality_stage"))
        
        #A B C D G 
        if person.infection is not None: #Infected Person. 
        # Get the current symptom tag of the person
            symptoms_tag = person.infection.tag

            #C D
            # Check if the person requires hospitalisation
            if symptoms_tag in hospitalised_tags:

                # Check if the person is already in a hospital
                if (
                    person.medical_facility is not None
                    and person.medical_facility.group.spec == "hospital"
                ):
                    patient_hospital = person.medical_facility.group
                else:
                    # Assign the closest hospital
                    patient_hospital = person.super_area.closest_hospitals[0]

                # Allocate the patient to the hospital
                status = patient_hospital.allocate_patient(person)

                if person.test_and_trace is not None: #D
                    if person.test_and_trace.scheduled_test_time is not None:
                        person.test_and_trace = None #We delete their TT to start from scratch

                # Record hospital admissions
                if record is not None:
                    if status in ["ward_admitted"]:
                        record.accumulate(
                            table_name="hospital_admissions",
                            hospital_id=patient_hospital.id,
                            patient_id=person.id,
                        )
                    elif status in ["icu_transferred"]:
                        record.accumulate(
                            table_name="icu_admissions",
                            hospital_id=patient_hospital.id,
                            patient_id=person.id,
                        )
                #C D
                return True 
            #Type A B G 
            else: #Person doesn't have symptoms to be hospitalised 
                # Check if the person is in a hospital but no longer requires care
                #G 
                if (
                    person.medical_facility is not None
                    and person.medical_facility.group.spec == "hospital"
                    and symptoms_tag not in dead_hospital_tags
                ): 
                    if person.test_and_trace is not None: #If We have policies active...
                        if self.debug:
                            print(f"Person {person.id} Haven't got their results back, CAN'T Leave hospital yet")
                            print(f"Person {person.id} is hospitalised? {person.hospitalised}. Results time: {person.test_and_trace.time_of_result}")

                        if person.test_and_trace.test_result is not None: #People are not released unless they got their results back
                            if self.debug:
                                print(f"Person {person.id} got their results back, and are now leaving hospital")
                            
                            # Log discharges
                            if record is not None:
                                record.accumulate(
                                    table_name="discharges",
                                    hospital_id=person.medical_facility.group.id,
                                    patient_id=person.id,
                                )
                            person.medical_facility.group.release_patient(person)
                        #G
                        return True
                        
                    else: #If we don't have policies active
                        if record is not None:
                            record.accumulate(
                                table_name="discharges",
                                hospital_id=person.medical_facility.group.id,
                                patient_id=person.id,
                            )
                        person.medical_facility.group.release_patient(person)
                        #G
                        return True
        #B F
        if person.test_and_trace is not None:
            if person.test_and_trace.test_result is None:
                if self.debug:
                    print(f"[Rank {mpi_rank}] Person {person.id} is bypassing hospitalization. Going to Testing Policy.")
                #B F
                return True 
        #A
        return False 

    
class Testing(MedicalCarePolicy):
    """
    Testing policy for patients arriving at the hospital.
    Implements a test with configurable accuracy to determine if a patient is infected.
    Results are scheduled to be available after a configured delay.
    """

    def __init__(
        self, 
        disease_config: DiseaseConfig, 
        start_time: Union[str, datetime.datetime] = "1900-01-01",
        end_time: Union[str, datetime.datetime] = "2100-01-01"
    ):
        """
        Initialize the testing policy.

        Parameters
        ----------
        disease_config : DiseaseConfig
            Configuration object for the disease.
        start_time : str
            Start time for the policy.
        end_time : str
            End time for the policy.
        accuracy : float
            Test accuracy (0-1).
        results_delay : int
            Number of days until test results are available.
        """
        super().__init__(start_time, end_time, disease_config)
        testing_data = disease_config.policy_manager.get_policy_data("testing")
        self.test_accuracy = testing_data.get("test_accuracy")
        self.results_delay = testing_data.get("results_delay")
        
        # Debug flag - set to False by default
        self.debug = False

        if self.debug:
            print(f"Testing policy initialized with accuracy={self.test_accuracy}, results_delay={self.results_delay}")

    def apply(self, person: Person, days_from_start: float = None, record: Optional[Record] = None, simulator = None) -> bool:
        """
        Apply the testing policy to a person.
        Now handles both hospitalized patients and notified contacts.
        """

        # Check if person is already waiting for a test but hasn't been tested yet
        if (person.hospitalised and
            person.test_and_trace is not None and 
            person.test_and_trace.time_of_testing is None and
            person.test_and_trace.scheduled_test_time is not None and
            days_from_start < person.test_and_trace.scheduled_test_time):
            # They're already scheduled for testing as a contact, don't create a duplicate test
            # Just accelerate their test to now since they're hospitalized
            person.test_and_trace.scheduled_test_time = days_from_start
            if self.debug:
                print(f"[Rank {mpi_rank}] Person {person.id} had a scheduled test that was accelerated due to hospitalization")

        if person.hospitalised and person.test_and_trace is None: #First time coming here, entered via hospitalisation
            person.test_and_trace = TestAndTrace()
        elif person.hospitalised and person.test_and_trace.test_result is not None: #They are hospitalised but are tested already
            return False

        # Check if person is a notified contact due for testing
        is_contact_for_testing = False
        if person.test_and_trace is not None and person.test_and_trace.notification_time is not None:
            if (days_from_start >= person.test_and_trace.scheduled_test_time):
                is_contact_for_testing = True
                if self.debug:
                    print(f"[Rank {mpi_rank}] Person {person.id} is marked as 'contact_for_testing'")
        
        # Apply testing if either condition is met
        if person.hospitalised or is_contact_for_testing:
            # Test already taken? Check if they have a scheduled time of result
            if person.test_and_trace.time_of_result is not None:
                
                # Check if it's time for the result to be available
                if days_from_start >= person.test_and_trace.time_of_result:
                    # Update the test result from pending to final
                    person.test_and_trace.test_result = person.test_and_trace.pending_test_result
                    
                    #Delete the pre-determined result
                    person.test_and_trace.pending_test_result = None
                    
                    if self.debug:
                        print(f"[Rank {mpi_rank}] Test result now available for person {person.id}: {person.test_and_trace.test_result}. Current time: {days_from_start}")

                    #if person.hospitalised is False and tat.test_result=="Positive":
                    if person.test_and_trace.test_result == "Negative":
                        person.test_and_trace = None
                        if self.debug:
                            print(f"[Rank {mpi_rank}] Person {person.id} tested Negative. Are they infected? {person.infected}. Releasing.")
                        return False                        
                            
                    # Return True only if the result is positive to trigger tracing
                    return person.test_and_trace.test_result == "Positive"
                
                return False
            
            # Person hasn't been tested yet - perform initial test
            person.test_and_trace.time_of_testing = days_from_start
            
            # Pre-determine the test result
            is_accurate = random.random() < self.test_accuracy

            if person.infected:
                # Store the predetermined result to be revealed later
                person.test_and_trace.pending_test_result = "Positive" if is_accurate else "Negative"
            else:
                person.test_and_trace.pending_test_result = "Negative" if is_accurate else "Positive"
                
            # Schedule when the result will be available
            person.test_and_trace.time_of_result = person.test_and_trace.time_of_testing + self.results_delay

            #Record
            emit_test_event(person, person.test_and_trace.time_of_result, person.test_and_trace.pending_test_result)
            
            if self.debug or False:  
                print(f"[Rank {mpi_rank}]"
                    f"Test performed for person {person.id} at {days_from_start}. "
                    f"Predetermined result: {person.test_and_trace.pending_test_result}. "
                    f"Result will be available at day {person.test_and_trace.time_of_result}"
                )

            # Only track positive tests in the pending list
            if person.test_and_trace.pending_test_result == "Positive":
                simulator.contact_manager.tests_ids_pending.append({
                    "person_id": person.id,
                    "result_time": person.test_and_trace.time_of_result,
                    "residence_id": person.residence.group.id,
                    "residence_spec": person.residence.group.spec,
                    "primary_activity_spec": person.primary_activity.spec if person.primary_activity is not None else -1,
                    "primary_activity_group_id": person.primary_activity.group.id if person.primary_activity is not None else -1,
                    "primary_activity_subgroup_type": person.primary_activity.subgroup_type if person.primary_activity is not None else -1,
                    "is_pa_external": True if person.primary_activity is not None and person.primary_activity.external else False,
                    "pa_domain_id": person.primary_activity.domain_id if person.primary_activity is not None and person.primary_activity.external else -1
                })
                

            # Test was performed but results aren't available yet
            return False

        return False
    
class Tracing(MedicalCarePolicy):
    """
    This class is in charge of identifying and tracing contacts of a person who tests positive.
    """

    def __init__(
        self, 
        disease_config: DiseaseConfig, 
        start_time: Union[str, datetime.datetime] = "1900-01-01",
        end_time: Union[str, datetime.datetime] = "2100-01-01",
    ):
        super().__init__(start_time, end_time, disease_config)
        
        # Load tracing-specific configuration
        tracing_data = disease_config.policy_manager.get_policy_data("tracing")
        self.max_contacts_to_trace = tracing_data.get("max_contacts_to_trace", 50)
        
        # Debug flag - set to False by default
        self.debug = False
        
        if self.debug:
            print(f"Tracing policy initialized with max_contacts_to_trace={self.max_contacts_to_trace}")
              
    
    def apply(self, person: Person, days_from_start: float = None, record: Optional[Record] = None, simulator = None) -> bool:
        
        pass
        
       