import random
import logging
from collections import defaultdict
import time
import numpy as np
from june.demography.person import Person
from june.epidemiology.test_and_trace import TestAndTrace
from june.mpi_wrapper import mpi_rank, mpi_available, mpi_comm, MPI, mpi_size
from june.records.event_recording import emit_trace_event

logger = logging.getLogger("contact_manager")

# Format for debug prints to include MPI rank
RANK_PREFIX = f"[RANK {mpi_rank}] " if mpi_available else ""

def debug_print(msg):
    """Helper function for consistent debug prints"""
    print(f"{RANK_PREFIX}{msg}")

plurals = {
    "university": "universities",
    "company": "companies"
}

class ContactManager:
    """
    Centralised manager for tracking contacts between people.
    
    This class maintains records of known contacts between people, particularly
    leisure companions for social interactions. It supports contact tracing for manual track and trace.
    """
    def __init__(self, simulation):
        """
        Initialize the centralised contact manager.
        
        Parameters
        ----------
        simulation : Simulator
            The simulation instance this contact manager belongs to
        """
        debug_print("Initialising ContactManager")
        self.simulation = simulation
        
        # Contact storage
        self.leisure_companions = defaultdict(dict)  # Person ID -> dict of leisure companion ID: {'timestamp': timestamp, 'activity': activity_type}
        
        # Cleanup and processing state
        self.last_cleanup = 0  # Timestamp of last cleanup
        self.tests_ids_pending = []  # List of pending test results
        
        # MPI communication state
        self.round2_notifications = [[] for _ in range(mpi_size)] if mpi_available and mpi_size > 1 else [[]]
        self.need_round2 = False
        
        # Cache for efficient lookups
        self._residence_cache = {}
        self._cache_built = False
        self._build_residence_cache()
        
        debug_print("ContactManager initialised")

    def _build_residence_cache(self):
        """Build a cache mapping residence_id -> residence_object for fast lookups."""
        debug_print("Building residence cache...")
        cache_start_time = time.time()
        
        world = self.simulation.world
        self._residence_cache = {}
        
        # Cache households
        if hasattr(world, 'households') and world.households is not None:
            for household in world.households.members:
                self._residence_cache[('household', household.id)] = household
        
        # Cache care homes  
        if hasattr(world, 'care_homes') and world.care_homes is not None:
            for care_home in world.care_homes.members:
                self._residence_cache[('care_home', care_home.id)] = care_home
        
        cache_time = time.time() - cache_start_time
        debug_print(f"Residence cache built with {len(self._residence_cache)} entries in {cache_time:.3f}s")
        self._cache_built = True
    
    
    def clean_old_contacts(self, current_timestamp, days_to_remember=10, force=False):
        """
        Clean old contacts, but only once per day unless forced.
        
        Parameters
        ----------
        current_timestamp : float
            Current simulation timestamp in day format (e.g., 3.5 = day 4 at noon)
        days_to_remember : int, optional
            Number of days to retain contacts, by default 10
        force : bool, optional
            Force cleanup regardless of time since last cleanup, by default False
        """
        if not force and current_timestamp - self.last_cleanup < 1.0:
            debug_print(f"Skipping cleanup, last was at {self.last_cleanup}, current is {current_timestamp}")
            return
        
        cutoff_timestamp = current_timestamp - days_to_remember
        debug_print(f"Cleaning contacts older than {days_to_remember} days (cutoff: {cutoff_timestamp})")
        
        # Clean leisure companions
        leisure_cleaned = self._clean_leisure_companions(cutoff_timestamp)
        
        debug_print(f"Cleaned {leisure_cleaned} leisure companions")
        self.last_cleanup = current_timestamp 

    def _clean_leisure_companions(self, cutoff_timestamp):
        """Clean leisure companions older than cutoff timestamp."""
        cleaned_count = 0
        for person_id in self.leisure_companions:
            before_len = len(self.leisure_companions[person_id])
            self.leisure_companions[person_id] = {
                companion_id: companion_info 
                for companion_id, companion_info in self.leisure_companions[person_id].items()
                if companion_info['timestamp'] >= cutoff_timestamp
            }
            cleaned_count += before_len - len(self.leisure_companions[person_id])
        return cleaned_count
    
    def process_test_results(self, current_time):
        """
        Process pending test results and notify contacts when appropriate.
        Includes MPI communication to handle cross-rank notifications.
        """
        # Separate ready and pending tests
        to_process, still_pending = self._separate_ready_tests(current_time)
        self.tests_ids_pending = still_pending
        
        # Initialize cross-rank notifications
        round1_notifications = [[] for _ in range(mpi_size)] if mpi_available and mpi_size > 1 else [[]]
        
        # Process each positive test result
        for test_info in to_process:
            self._process_single_test_result(test_info, current_time, round1_notifications)

        # Handle MPI communication if needed
        if mpi_available and mpi_size > 1:
            self._handle_mpi_communication(round1_notifications)

    def _separate_ready_tests(self, current_time):
        """Separate tests that are ready for processing from those still pending."""
        to_process = []
        still_pending = []
        
        for test_info in self.tests_ids_pending:
            if current_time >= test_info["result_time"]:
                to_process.append(test_info)
            else:
                still_pending.append(test_info)
        
        return to_process, still_pending

    def _process_single_test_result(self, test_info, current_time, round1_notifications):
        """Process a single positive test result and notify contacts."""
        person_id = test_info["person_id"]
        
        # Collect all types of contacts
        housemates_ids = self._collect_housemates(test_info)
        locals_to_notify, total_ext_mates = self._collect_activity_contacts(test_info, round1_notifications)
        local_leisure_companions, external_leisure_companions = self._collect_leisure_contacts(person_id, round1_notifications)
        
        # Combine all local contacts
        all_local_contacts = housemates_ids | locals_to_notify | local_leisure_companions
        
        if all_local_contacts:
            total_mates = len(housemates_ids) + total_ext_mates + external_leisure_companions
            emit_trace_event(person_id, total_mates, current_time)
            
            # Notify each contact with appropriate reason
            self._notify_local_contacts(all_local_contacts, housemates_ids, locals_to_notify, 
                                       local_leisure_companions, person_id, current_time)

    def _collect_activity_contacts(self, test_info, round1_notifications):
        """Collect activity-based contacts (colleagues)."""
        if test_info["primary_activity_spec"] in [-1, "hospital"]:
            return set(), 0
        
        return self._collect_activitymates(test_info, round1_notifications)

    def _collect_leisure_contacts(self, person_id, round1_notifications):
        """Collect leisure companions for contact tracing."""
        return self._collect_leisure_companions(person_id, round1_notifications)

    def _notify_local_contacts(self, all_contacts, housemates, colleagues, leisure_companions, tracer_id, current_time):
        """Notify all local contacts with appropriate contact reasons."""
        for contact_id in all_contacts:
            # Determine contact reason
            if contact_id in housemates:
                contact_reason = 'housemate'
            elif contact_id in colleagues:
                contact_reason = 'colleague'
            elif contact_id in leisure_companions:
                contact_reason = 'leisure'
            else:
                contact_reason = 'unknown'
            
            self.notify_person(contact_id, current_time, tracer_id=tracer_id, contact_reason=contact_reason)

    def _handle_mpi_communication(self, round1_notifications):
        """Handle MPI communication for cross-rank notifications."""
        mpi_comm.Barrier()
        
        # Check if any rank has notifications for round 1
        local_has_notifications = 1 if any(len(notifications) > 0 for notifications in round1_notifications) else 0
        notification_counts = mpi_comm.allgather(local_has_notifications)
        
        if any(notification_counts):
            self.need_round2 = False
            self._exchange_notifications_non_blocking(round1_notifications, round_id=0)
            
            # Check if second round is needed
            local_need_round2 = 1 if self.need_round2 else 0
            global_need_round2 = mpi_comm.allreduce(local_need_round2, op=MPI.LOR)
            
            if global_need_round2:
                self._exchange_notifications_non_blocking(self.round2_notifications, round_id=1)
                self.round2_notifications = [[] for _ in range(mpi_size)]
        else:
            mpi_comm.Barrier()
        
        mpi_comm.Barrier()

    def _collect_housemates(self, test_info):
        # Build cache if not already built
        if not self._cache_built:
            self._build_residence_cache()
        
        person_id = test_info["person_id"]
        residence_id = test_info["residence_id"]
        residence_spec = test_info["residence_spec"]
        
        cache_key = (residence_spec, residence_id)
        residence = self._residence_cache.get(cache_key)
        
        if residence is None:
            debug_print(f"Warning: Residence {residence_spec} ID {residence_id} not found in cache")
            return set()
        
        # Collect housemates efficiently
        housemates_ids = set()
        for resident in residence.residents:
            if resident.id != person_id:  # Don't include the infected person
                housemates_ids.add(resident.id)
        
        return housemates_ids
    
    def _collect_leisure_companions(self, person_id, cross_rank_notifications=None):
        """
        Collect leisure companions for contact tracing.
        
        Parameters
        ----------
        person_id : int
            ID of the infected person
        cross_rank_notifications : list, optional
            List for storing cross-rank notifications
            
        Returns
        -------
        tuple
            (set of local leisure companion IDs, count of external companions)
        """        
        local_leisure_companions = set()
        external_leisure_companions = 0
                
        for companion_id, companion_info in self.leisure_companions.get(person_id, {}).items():
            companion_home_rank = companion_info.get('home_rank', mpi_rank)
                        
            if companion_home_rank == mpi_rank:
                # Local companion - check if they're actually on this rank
                from june.demography.person import Person
                companion = Person.find_by_id(companion_id)
                
                if companion is not None:  # Local companion
                    local_leisure_companions.add(companion_id)
            else:
                # Remote companion - add to cross-rank notifications
                external_leisure_companions += 1
                
                if cross_rank_notifications is not None:
                    cross_rank_notifications[companion_home_rank].append({
                        'notif_type': 'notify_person',
                        'person_to_notify': companion_id,
                        'tracer_id': person_id,
                        'contact_reason': 'leisure'
                    })
        
        return local_leisure_companions, external_leisure_companions
    
    def _collect_activitymates(self, test_info, cross_rank_notifications):
        subgroup = self._find_primary_activity(test_info)
        
        locals_to_notify = set()
        total_ext_mates = 0
        #If subgroup is not None, means activity is local
        if subgroup is not None: 
            person_id = test_info["person_id"]
            locals_to_notify, total_ext_mates = self._identify_activitymates_locations(subgroup, person_id, cross_rank_notifications)
        else: #Activity is external
            self._find_external_primary_activity_mates(test_info, cross_rank_notifications)

        return locals_to_notify, total_ext_mates
    
    def _find_primary_activity(self, test_info):
        pa_spec = test_info["primary_activity_spec"]
        pa_id = test_info["primary_activity_group_id"]
        pa_subgroup = test_info["primary_activity_subgroup_type"]

        world = self.simulation.world

        group_type = getattr(world, plurals.get(pa_spec, pa_spec + 's'))

        primary_activity_group = None
        primary_activity_subgroup = None
        for group in group_type.members:
            if group.id == pa_id:
               primary_activity_group = group
               break
        
        if primary_activity_group is not None:
            for subgroup in primary_activity_group.subgroups:
                if subgroup.subgroup_type == pa_subgroup:
                    primary_activity_subgroup = subgroup
                    break

        return primary_activity_subgroup

    def _identify_activitymates_locations(self, subgroup, person_id, cross_rank_notifications):
        local_activity_mates = set()
        external_mates = 0
        max_contacts = 50  # Maximum number of contacts to sample

        if hasattr(subgroup.group, "registered_members_ids"):
            # Check if the group has a dictionary of members by subgroup type
            registered_members = subgroup.group.registered_members_ids
            
            # If the registered_members is structured by subgroup type, get only the relevant subgroup
            subgroup_type = subgroup.subgroup_type
            if isinstance(registered_members, dict) and subgroup_type in registered_members:
                registered_members = {subgroup_type: registered_members[subgroup_type]}


        # Collect all relevant members
        all_members = []
        for key, members_list in registered_members.items():
            all_members.extend(members_list)
        
        # Remove the person themselves if they're in the list
        all_members = [member for member in all_members if member[0] != person_id]
        
        # Sample if there are too many members
        if len(all_members) > max_contacts:
            sampled_members = random.sample(all_members, max_contacts)
        else:
            sampled_members = all_members
        
        # Process the sampled members
        for member_tuple in sampled_members:
            member_id, member_home_rank = member_tuple
            
            # Check if member is on this rank
            if member_home_rank == mpi_rank:
                local_activity_mates.add(member_id)
            else:  # Member is not in rank
                external_mates += 1
                cross_rank_notifications[member_home_rank].append({
                    'notif_type': 'notify_person',
                    'person_to_notify': member_id,
                    'tracer_id': person_id,
                    'contact_reason': 'colleague'
                })
                
        return local_activity_mates, external_mates

    def _find_external_primary_activity_mates(self, test_info, cross_rank_notifications):
        external_activity_mates_request = self._generate_request_external_activity(test_info)
        
        pa_domain_id = test_info["pa_domain_id"]

        cross_rank_notifications[pa_domain_id].append(external_activity_mates_request)
    
    def _generate_request_external_activity(self, test_info):
        person_id = test_info["person_id"]
        pa_spec = test_info["primary_activity_spec"]
        pa_id = test_info["primary_activity_group_id"]
        pa_subgroup = test_info["primary_activity_subgroup_type"]

        external_activity_mates_request = {
            'notif_type': "mates_requests",
            'person_id': person_id,
            'pa_spec': pa_spec,
            'pa_id': pa_id,
            'pa_subgroup': pa_subgroup, 
        }
        return external_activity_mates_request
    
    def _exchange_notifications_non_blocking(self, cross_rank_notifications, round_id=0):
        """
        Exchange notifications using non-blocking communication.
        Works with any number of ranks and properly handles MPI requests.
        Includes chunking for large messages to prevent buffer overflow.
        
        Parameters
        ----------
        cross_rank_notifications : list
            A list of lists where index i contains notifications for rank i
        round_id : int, optional
            Identifier for the notification round (0 for first round, 1+ for subsequent rounds)
        """
        if not mpi_available or mpi_size <= 1:
            return
                
        # Maximum number of notifications to send in a single chunk
        # Adjust this value based on your data size and MPI buffer capacity
        MAX_CHUNK_SIZE = 400
        
        # PHASE 1: SIZE EXCHANGE WITH CHUNKING INFO
        # Now sending [total_notifications, num_chunks] to each rank
        send_sizes = []
        for target_rank in range(mpi_size):
            if target_rank != mpi_rank and cross_rank_notifications[target_rank]:
                total_notifs = len(cross_rank_notifications[target_rank])
                num_chunks = (total_notifs + MAX_CHUNK_SIZE - 1) // MAX_CHUNK_SIZE  # Ceiling division
                send_sizes.append([total_notifs, num_chunks])
            else:
                send_sizes.append([0, 0])
        
        # Exchange sizes using alltoall collective operation
        recv_sizes = mpi_comm.alltoall(send_sizes)
        
        # PHASE 2: DATA EXCHANGE WITH CHUNKING
        # Set up a custom buffer for MPI communication
        buffer_size = 20000000  # 20MB buffer, adjust as needed
        MPI.Attach_buffer(np.empty(buffer_size, dtype=np.uint8))
        
        # Keep track of all send and receive requests
        all_send_requests = []
        all_recv_buffers = []  # Store references to receive buffers
        chunk_data = {}  # To hold received chunks per source rank
        
        # Prepare to receive chunks from each rank
        for source_rank in range(mpi_size):
            if source_rank != mpi_rank and recv_sizes[source_rank][0] > 0:
                total_notifs = recv_sizes[source_rank][0]
                num_chunks = recv_sizes[source_rank][1]
                chunk_data[source_rank] = {
                    'num_chunks': num_chunks,
                    'received_chunks': 0,
                    'data_chunks': [None] * num_chunks
                }
                                
                # Post receive requests for each chunk
                for chunk_idx in range(num_chunks):
                    recv_tag = 100 + round_id*1000 + source_rank*100 + chunk_idx
                    req = mpi_comm.irecv(source=source_rank, tag=recv_tag)
                    all_recv_buffers.append((source_rank, chunk_idx, req))
        
        # Send chunks to each rank
        for target_rank in range(mpi_size):
            if target_rank != mpi_rank and send_sizes[target_rank][0] > 0:
                notifications = cross_rank_notifications[target_rank]
                total_notifs = len(notifications)
                num_chunks = (total_notifs + MAX_CHUNK_SIZE - 1) // MAX_CHUNK_SIZE
                                
                # Split and send notifications in chunks
                for chunk_idx in range(num_chunks):
                    start_idx = chunk_idx * MAX_CHUNK_SIZE
                    end_idx = min(start_idx + MAX_CHUNK_SIZE, total_notifs)
                    chunk = notifications[start_idx:end_idx]
                    
                    # Serialize the chunk
                    import pickle
                    serialized_chunk = pickle.dumps(chunk, protocol=4)  # Using protocol 4 for better handling of large objects
                    
                    # Use unique tag for each chunk
                    send_tag = 100 + round_id*1000 + mpi_rank*100 + chunk_idx
                                        
                    # Use isend for non-blocking send
                    req = mpi_comm.isend(serialized_chunk, dest=target_rank, tag=send_tag)
                    all_send_requests.append(req)
        
        # Wait for all sends to complete
        if all_send_requests:
            MPI.Request.waitall(all_send_requests)
        
        # Process receives - collect and process all chunks
        current_time = self.simulation.timer.now
        
        for source_rank, chunk_idx, req in all_recv_buffers:
            # Use wait() to complete the request
            serialized_chunk = req.wait()
            
            # Deserialize the chunk
            import pickle
            chunk = pickle.loads(serialized_chunk)
            
            # Store chunk data
            chunk_data[source_rank]['data_chunks'][chunk_idx] = chunk
            chunk_data[source_rank]['received_chunks'] += 1
            
            # If all chunks are received from this rank, process the notifications
            if chunk_data[source_rank]['received_chunks'] == chunk_data[source_rank]['num_chunks']:
                # Concatenate all chunks
                all_notifications = []
                for chunk in chunk_data[source_rank]['data_chunks']:
                    if chunk is not None:  # Safety check
                        all_notifications.extend(chunk)   
                
                # Process all notifications
                for notification in all_notifications:
                    self._process_received_notification(notification, current_time)
        
        # Detach buffer
        MPI.Detach_buffer()
        
        # Synchronize all ranks to ensure we're all ready for the next round
        mpi_comm.Barrier()

    def _process_received_notification(self, notification, current_time=None):
        """
        Process a notification received from another rank.
        """
        # Use the current time from the simulation if not provided
        if current_time is None:
            current_time = self.simulation.timer.now
        
        # Check the notification type and handle accordingly
        notif_type = notification.get('notif_type')
        
        if notif_type == 'notify_person':
            person_id = notification.get('person_to_notify')
            self.notify_person(person_id, current_time, tracer_id=notification.get('tracer_id'), contact_reason=notification.get('contact_reason'))
        
        elif notif_type == 'mates_requests':
            # Handle request for activity mates
            person_id = notification.get('person_id')
            pa_spec = notification.get('pa_spec')
            pa_id = notification.get('pa_id')
            pa_subgroup = notification.get('pa_subgroup')
            
            # Signal that we need a round 2
            self.need_round2 = True
            
            # Process the request to find activity mates
            self._process_activity_mates_request(person_id, pa_spec, pa_id, pa_subgroup, current_time)

        
    def notify_person(self, person_id, current_time, tracer_id=None, contact_reason=None):
        """
        Notify a person of potential exposure.
        
        Parameters
        ----------
        person_id : int
            ID of the person to notify
        current_time : float
            Current simulation timestamp in day format
        tracer_id : int, optional
            ID of the person who caused this contact tracing (the source)
        contact_reason : str, optional
            Reason for the contact ('housemate', 'colleague', 'leisure', etc.)
        """
        person = Person.find_by_id(person_id)

        if person.dead or person.hospitalised or person.test_and_trace is not None:
            return
        
        person.test_and_trace = TestAndTrace()
        person.test_and_trace.notification_time = current_time
        person.test_and_trace.scheduled_test_time = current_time
        
        # Store tracer information if provided
        if tracer_id is not None:
            person.test_and_trace.tracer_id = tracer_id
            person.test_and_trace.contact_reason = contact_reason or 'unknown'
        

    def _process_activity_mates_request(self, person_id, pa_spec, pa_id, pa_subgroup, current_time):
        """
        Process a request to find and notify activity mates of a person.
        
        This method is called when a request comes from another rank to find
        activity mates for a person who works in an activity that exists on this rank.
        
        Parameters
        ----------
        person_id : int
            ID of the person whose activity mates need to be found
        pa_spec : str
            Primary activity specification (e.g. "company", "school")
        pa_id : int
            ID of the primary activity group
        pa_subgroup : str
            Subgroup type within the primary activity
        current_time : float
            Current simulation timestamp in day format
        """        
        # Step 1: Find the activity group
        world = self.simulation.world
        group_type = getattr(world, plurals.get(pa_spec, pa_spec + 's'))
        
        primary_activity_group = None
        primary_activity_subgroup = None
        
        for group in group_type.members:
            if group.id == pa_id:
                primary_activity_group = group
                break
        
        if primary_activity_group is None:
            return
        
        # Step 2: Find the subgroup
        for subgroup in primary_activity_group.subgroups:
            if subgroup.subgroup_type == pa_subgroup:
                primary_activity_subgroup = subgroup
                break
        
        if primary_activity_subgroup is None:
            return
        
        # Step 3: Find activity mates in this group, excluding the original person
        # These will be added to round2_notifications if they're external
        local_activity_mates, total_ext_mates = self._identify_activitymates_locations(
            primary_activity_subgroup, person_id, self.round2_notifications
        )
        # Step 4: Notify local activity mates
        for mate_id in local_activity_mates:
            self.notify_person(mate_id, current_time, tracer_id=person_id, contact_reason='colleague')
        
        tot = len(local_activity_mates)+total_ext_mates

        emit_trace_event(person_id, tot, current_time)

    def add_leisure_companion(self, person_id, companion_id, activity_type, timestamp):
        """
        Add a leisure companion contact for a person.
        
        Parameters
        ----------
        person_id : int
            ID of the person
        companion_id : int
            ID of the leisure companion
        activity_type : str
            Type of leisure activity (e.g., 'pub', 'cinema')
        timestamp : float
            Timestamp when the leisure activity occurred
        """
        # Get the home ranks of both people
        from june.demography.person import Person
        
        person = Person.find_by_id(person_id)
        companion = Person.find_by_id(companion_id)
        
        person_home_rank = getattr(person, '_home_rank', mpi_rank) if person else mpi_rank
        companion_home_rank = getattr(companion, '_home_rank', mpi_rank) if companion else mpi_rank
                
        # Store with home rank information
        self.leisure_companions[person_id][companion_id] = {
            'timestamp': timestamp,
            'activity': activity_type,
            'home_rank': companion_home_rank
        }
        # Also add the reverse relationship
        self.leisure_companions[companion_id][person_id] = {
            'timestamp': timestamp,
            'activity': activity_type,
            'home_rank': person_home_rank
        }