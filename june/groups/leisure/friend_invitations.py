"""
Friend Invitation System for Leisure Activities

This module contains the data structures and logic for handling friend invitations
to leisure activities across MPI ranks.
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Optional
import random
from collections import defaultdict

from june.demography.person import Person
from june.groups.group.external import ExternalGroup, ExternalSubgroup
from june.groups.leisure.social_network import SocialNetwork
from june.mpi_wrapper import mpi_comm, mpi_rank, mpi_size

# MPI Tags for friend invitation communication
FRIEND_INVITATION_TAG = 300
FRIEND_RESPONSE_TAG = 400
FRIEND_DELEGATION_TAG = 500


@dataclass
class LeisureInvitation:
    """
    Data structure for a leisure activity invitation between friends.
    """
    inviter_id: int
    inviter_home_rank: int
    friend_id: int
    friend_home_rank: int
    venue_id: int
    activity_type: str  # "pub", "cinema", etc.
    subgroup_type: int
    
    def __hash__(self):
        return hash((self.inviter_id, self.friend_id))


@dataclass
class LeisureResponse:
    """
    Data structure for a response to a leisure invitation.
    """
    invitation: LeisureInvitation
    accepted: bool
    
    def __hash__(self):
        return hash(self.invitation)


class FriendInvitationManager:
    """
    Manages the friend invitation process for leisure activities.
    """
    
    def __init__(self, contact_manager=None):
        self.social_network = SocialNetwork()
        self.pending_invitations: List[LeisureInvitation] = []
        self.received_invitations: List[LeisureInvitation] = []
        self.pending_responses: List[LeisureResponse] = []
        self.received_responses: List[LeisureResponse] = []
        self.pending_delegations: List[dict] = []  # Queue for external inviter delegations
        self.received_delegations: List[dict] = []  # Delegations received from other ranks
        self.external_inviter_ids: Set[int] = set()  # Track external inviters by ID
        self.contact_manager = contact_manager
        self._simulator_cache = None  # Cache for simulator reference
        
    def _get_current_timestamp(self):
        """
        Get the current simulation timestamp using cached simulator reference.
        
        Returns
        -------
        float or None
            Current simulation timestamp, or None if simulator not available
        """
        if self._simulator_cache is None:
            from june.global_context import GlobalContext
            self._simulator_cache = GlobalContext.get_simulator()
        
        return self._simulator_cache.timer.now if (self._simulator_cache and self._simulator_cache.timer) else None
        
    def _clear_simulator_cache(self):
        """
        Clear the cached simulator reference. Useful for testing or when simulator changes.
        """
        self._simulator_cache = None
        
    def clear(self):
        """Clear all pending data for the next timestep."""
        self.pending_invitations.clear()
        self.received_invitations.clear()
        self.pending_responses.clear()
        self.received_responses.clear()
        self.pending_delegations.clear()
        self.received_delegations.clear()
        self.external_inviter_ids.clear()
        # Note: We keep _simulator_cache as it should remain valid across timesteps
    
    def generate_invitations(self, potential_inviters: List[Person]) -> None:
        """
        Generate invitations from people who won the invite lottery.
        
        Parameters
        ----------
        potential_inviters : List[Person]
            People who are doing leisure activities and might invite friends
        """
        
        invitation_count = 0
        people_with_friends = 0
        people_who_rolled_to_invite = 0
        total_local_invitations = 0
        total_local_accepted = 0
        total_local_rejected = 0
        total_housemates_invitations = 0
        total_housemates_accepted = 0
        total_housemates_rejected = 0
        
        for i, person in enumerate(potential_inviters):
            # Check if this person's activity has invites_friends_probability
            if person.subgroups.leisure is None:
                continue
            
            # Handle external vs local inviters differently
            if person.id in self.external_inviter_ids:
                # NEW: Handle external inviters via delegation
                self._handle_external_inviter(person)
                continue
                
            # EXISTING: Handle local inviters
            # Get the activity distributor to check invite probability
            activity_distributor = self._get_activity_distributor(person)
            if activity_distributor is None:
                continue
            
            # Check if person has friends
            if not person.friends:
                continue
            
            people_with_friends += 1
            chosen_group = None
            chosen_group = self.which_group_is_person_inviting(person, activity_distributor)

            if chosen_group is not None:
                people_who_rolled_to_invite += 1
                if chosen_group == "friends":
                    local_accepted, local_rejected = self.person_chose_friends(person)
                    total_local_invitations += (local_accepted + local_rejected)
                    total_local_accepted += local_accepted
                    total_local_rejected += local_rejected
                if chosen_group == "household":
                    housemates_accepted, housemates_rejected = self.person_chose_household(person)
                    total_housemates_invitations += (housemates_accepted + housemates_rejected)
                    total_housemates_accepted += housemates_accepted
                    total_housemates_rejected += housemates_rejected

        invitation_count = len(self.pending_invitations)
        delegation_count = len(self.pending_delegations)
        print(f"[Rank {mpi_rank}] generate_invitations: SUMMARY - {len(potential_inviters)} inviters, "
              f"{people_with_friends} with friends, "
              f"{people_who_rolled_to_invite} rolled to invite, "
              f"{invitation_count} cross-rank friend invitations created, "
              f"{delegation_count} external delegations queued, "
              f"{total_local_invitations} local friend invitations ({total_local_accepted} accepted, {total_local_rejected} rejected), "
              f"{total_housemates_invitations} housemate invitations ({total_housemates_accepted} accepted, {total_housemates_rejected} rejected)")
        

    
    def which_group_is_person_inviting(self, person, activity_distributor):

        activity_type = activity_distributor.spec

        priority = self.social_network.decide_target_group_invitation(person, activity_type)
        actions = {
            "household": activity_distributor.person_drags_household,
            "friends": activity_distributor.person_invites_friends,
        }

        # Try primary priority
        if actions[priority]():
            if priority == "household":
                #print(f"Priority is household, and we rolled household")
                return "household"
            else:
                #print(f"Priority is friends and we rolled friends")
                return "friends"
        else:
            # Try fallback priority
            other_priority = "friends" if priority == "household" else "household"
            if actions[other_priority]():
                if other_priority == "household":
                    #print(f"Priority was friends, but now we are trying household")
                    return "household"
                else:
                    #print(f"Priority was household, but we are now trying friends")
                    return "friends"

        return


    def person_chose_friends(self, person):
        """
        Handle a person inviting friends to their leisure activity.
        Processes both same-rank and cross-rank invitations immediately.
        
        Returns
        -------
        tuple
            (local_accepted, local_rejected) counts
        """
        # Person wants to invite friends
        friends_to_invite = self._select_friends_to_invite(person)
        
        same_rank_friends = []
        cross_rank_invitations = []
        
        for friend_id in friends_to_invite:
            friend_home_rank = self._get_friend_home_rank(person, friend_id)
            
            if friend_home_rank == mpi_rank:
                # Same rank - process immediately
                same_rank_friends.append(friend_id)
            else:
                # Cross rank - create invitation for MPI exchange
                invitation = LeisureInvitation(
                    inviter_id=person.id,
                    inviter_home_rank=person._home_rank,
                    friend_id=friend_id,
                    friend_home_rank=friend_home_rank,
                    venue_id=person.subgroups.leisure.group.id,
                    activity_type=person.subgroups.leisure.spec,
                    subgroup_type=person.subgroups.leisure.subgroup_type
                )
                cross_rank_invitations.append(invitation)
        
        # Process same-rank friends immediately
        local_accepted, local_rejected = 0, 0
        if same_rank_friends:
            local_accepted, local_rejected = self._process_same_rank_invites(person, same_rank_friends)
        
        # Add cross-rank invitations to pending list for MPI exchange
        self.pending_invitations.extend(cross_rank_invitations)
        
        return local_accepted, local_rejected
    
    def _process_same_rank_invites(self, inviter: Person, invited_ids: List[int]):
        """
        Process friend invitations for friends on the same rank immediately.
        
        Parameters
        ----------
        inviter : Person
            The person doing the inviting
        invited_ids : List[int]
            List of IDs to invite on the same rank
            
        Returns
        -------
        tuple
            (accepted_count, rejected_count)
        """        
        accepted_count = 0
        rejected_count = 0
        
        for invited_id in invited_ids:
            invited_person = Person.find_by_id(invited_id)
            if invited_person is None:
                print(f"[Rank {mpi_rank}] _process_same_rank_friends: WARNING - Friend {invited_id} not found")
                rejected_count += 1
                continue
            
            # Check if friend already accepted an invitation this round
            if hasattr(invited_person, '_accepted_invitation_this_round') and invited_person._accepted_invitation_this_round:
                rejected_count += 1
                continue
            
            # Decision logic (same as process_invitations)
            if invited_person.subgroups.leisure is None:
                if invited_person.busy:
                    #Friend is not doing leisure and is working
                    accept = False
                else:
                    # Friend wasn't doing leisure, easy accept
                    accept = True
            else:
                # Friend was doing solo leisure, 80% acceptance rate
                accept = random.random() < 0.8
            
            if accept:
                accepted_count += 1
                invited_person._accepted_invitation_this_round = True
                
                # Remove from original leisure subgroup if they had one
                if invited_person.subgroups.leisure is not None:
                    original_subgroup = invited_person.subgroups.leisure
                    # Skip ExternalSubgroups - they don't have a 'people' attribute
                    if hasattr(original_subgroup, 'external') and original_subgroup.external:
                        # Just clear the reference for external subgroups
                        invited_person.subgroups.leisure = None
                    elif invited_person in original_subgroup.people:
                        original_subgroup.remove(invited_person)
                        invited_person.subgroups.leisure = None
                
                # Assign friend directly to inviter's subgroup (same rank!)
                inviter_subgroup = inviter.subgroups.leisure
                if inviter_subgroup is not None:
                    inviter_subgroup.append(invited_person)
                    
                    # Record temporary contact between inviter and invited friend
                    # Only record if this is NOT a household member (since they are already permanent contacts)
                    if self.contact_manager is not None and not self._are_household_members(inviter, invited_person):
                        # Get current timestamp using cached simulator
                        current_timestamp = self._get_current_timestamp()
                        if current_timestamp is not None:
                            activity_type = inviter_subgroup.spec
                            
                            # Record the leisure companion relationship
                            self.contact_manager.add_leisure_companion(
                                person_id=inviter.id,
                                companion_id=invited_id,
                                activity_type=activity_type,
                                timestamp=current_timestamp
                            )
            else:
                rejected_count += 1
        
        return accepted_count, rejected_count

    def _get_activity_distributor(self, person: Person):
        """Get the activity distributor for this person's current leisure activity."""
        # We need access to the leisure system to get the distributor
        # This will be passed in when we integrate with ActivityManager
        # For now, we'll assume it's accessible through the person's subgroup
        if hasattr(person.subgroups.leisure, '_activity_distributor'):
            return person.subgroups.leisure._activity_distributor
        return None
    
    def _select_friends_to_invite(self, person: Person) -> List[int]:
        """
        Select friends to invite based on stored hobbies information.
        
        Parameters
        ----------
        person : Person
            The person doing the inviting
            
        Returns
        -------
        List[int]
            List of friend IDs to invite
        """
        DEBUG = False  # Set to True for detailed debugging
        
        if not person.friends:
            if DEBUG:
                print(f"[DEBUG] Person {person.id} has no friends.")
            return []
        
        # Convert friend data to objects for hobby-based selection
        friend_objects = []
        for friend_id, friend_data in person.friends.items():
            
            stored_hobbies = friend_data.get("hobbies", [])
            
            # Create a temporary object to hold friend info for selection logic
            friend_obj = type('Friend', (), {
                'id': friend_id,
                'hobbies': stored_hobbies
            })()
            friend_objects.append(friend_obj)
        
        if not friend_objects:
            if DEBUG:
                print(f"[DEBUG] Person {person.id} has friends, but none could be processed.")
            return []
        
        if DEBUG:
            print(f"[DEBUG] Person {person.id} is inviting friends. Hobbies: {person.hobbies}")
        
        # Step 1: Compute base weights for initial selection
        base_weights = {}
        for friend_obj in friend_objects:
            shared_hobbies = set(person.hobbies) & set(friend_obj.hobbies)
            base_weights[friend_obj] = len(shared_hobbies) + 1
            if DEBUG:
                print(f"[DEBUG] Friend {friend_obj.id} shared hobbies: {shared_hobbies}, base weight: {base_weights[friend_obj]}")
        
        total_weight = sum(base_weights.values())
        normalized_base_weights = {f: w / total_weight for f, w in base_weights.items()}
        if DEBUG:
            print(f"[DEBUG] Normalized base weights: {[f'{f.id}: {w:.4f}' for f, w in normalized_base_weights.items()]}")
        
        # Step 2: Choose the "first friend" using these normalized base weights
        first_friend = random.choices(
            population=list(normalized_base_weights.keys()),
            weights=list(normalized_base_weights.values()),
            k=1
        )[0]
        if DEBUG:
            print(f"[DEBUG] First friend selected: Friend {first_friend.id}")
        
        # Step 3: Determine eligibility for bonus based on shared hobbies with first friend
        shared_with_first = set(person.hobbies) & set(first_friend.hobbies)
        
        eligibility_bonus = {}
        for friend_obj in friend_objects:
            if shared_with_first & set(friend_obj.hobbies):
                eligibility_bonus[friend_obj] = len(shared_with_first & set(friend_obj.hobbies)) + 1
            else:
                eligibility_bonus[friend_obj] = 0
        
        if DEBUG:
            print(f"[DEBUG] Eligibility bonus: {[f'{f.id}: {bonus}' for f, bonus in eligibility_bonus.items()]}")
        
        # Step 4: Assign independent invitation probabilities
        baseline_prob = 0.05     # 5% chance for non-eligible friends
        bonus_multiplier = 0.25  # Each bonus point adds extra probability
        invitation_probabilities = {}
        for friend_obj in friend_objects:
            invitation_probabilities[friend_obj] = baseline_prob + bonus_multiplier * eligibility_bonus.get(friend_obj, 0)
            if DEBUG:
                print(f"[DEBUG] Friend {friend_obj.id}: invitation probability set to {invitation_probabilities[friend_obj]:.4f}")
        
        # Step 5: Roll independently for each friend
        invitations = []
        for friend_obj, p in invitation_probabilities.items():
            r = random.random()
            if DEBUG:
                print(f"[DEBUG] Friend {friend_obj.id}: rolled {r:.4f} (needs < {p:.4f})")
            if r < p:
                invitations.append(friend_obj)
                if DEBUG:
                    print(f"[DEBUG] Friend {friend_obj.id} IS invited!")
            else:
                if DEBUG:
                    print(f"[DEBUG] Friend {friend_obj.id} is NOT invited.")
        
        # Ensure the first friend is always invited
        if first_friend not in invitations:
            if DEBUG:
                print(f"[DEBUG] First friend ({first_friend.id}) was not invited by the roll; adding explicitly.")
            invitations.insert(0, first_friend)
        else:
            if DEBUG:
                print(f"[DEBUG] First friend ({first_friend.id}) is already invited by the roll.")
        
        if DEBUG:
            print(f"[DEBUG] Final invitations: {[f.id for f in invitations]}")
        
        # Return list of friend IDs
        return [f.id for f in invitations]
    
    def _get_friend_home_rank(self, person: Person, friend_id: int) -> int:
        """
        Get the home rank of a friend by their ID using the stored home_rank.
        
        Parameters
        ----------
        person : Person
            The person whose friend we're looking up
        friend_id : int
            ID of the friend
            
        Returns
        -------
        int
            Home rank of the friend
        """
        # Handle both old format (just home_rank) and new format (dict)
        friend_data = person.friends[friend_id]
        if isinstance(friend_data, dict):
            return friend_data.get("home_rank", 0)
        else:
            # Old format - just the home_rank value
            return friend_data
    
    def exchange_invitations(self) -> None:
        """
        Send all pending invitations to appropriate ranks and receive invitations from other ranks.
        """
        
        # Add MPI barrier to ensure all ranks reach this point
        mpi_comm.Barrier()
        
        # Organize invitations by destination rank
        invitations_by_rank = defaultdict(list)
        for invitation in self.pending_invitations:
            if invitation.friend_home_rank >= 0 and invitation.friend_home_rank < mpi_size:  # Valid rank
                invitations_by_rank[invitation.friend_home_rank].append(invitation)
            else:
                print(f"[Rank {mpi_rank}] exchange_invitations: WARNING - Invalid rank {invitation.friend_home_rank} for invitation {invitation.inviter_id}->{invitation.friend_id}")
                
        # Use non-blocking sends to avoid deadlock
        send_requests = []
        
        # Send invitations to each rank using non-blocking sends
        for rank in range(mpi_size):
            if rank == mpi_rank:
                continue
            
            invitations_for_rank = invitations_by_rank.get(rank, [])
            
            req = mpi_comm.isend(invitations_for_rank, dest=rank, tag=FRIEND_INVITATION_TAG)
            send_requests.append(req)
        
        # Receive invitations from each rank
        self.received_invitations.clear()
        total_received = 0
        for rank in range(mpi_size):
            if rank == mpi_rank:
                continue
            

            received = mpi_comm.recv(source=rank, tag=FRIEND_INVITATION_TAG)
            self.received_invitations.extend(received)
            total_received += len(received)
        
        # Wait for all sends to complete
        for i, req in enumerate(send_requests):
            req.wait()
            
    def process_invitations(self, potential_inviters: List[Person]) -> None:
        """
        Process received invitations and generate responses.
        
        Parameters
        ----------
        potential_inviters : List[Person]
            People who were planning to invite others (used for decision making)
        """
        
        potential_inviter_ids = {person.id for person in potential_inviters}
        
        # Group invitations by friend_id to handle multiple invitations to same person
        invitations_by_friend = defaultdict(list)
        for invitation in self.received_invitations:
            invitations_by_friend[invitation.friend_id].append(invitation)
        
        accepted_count = 0
        rejected_count = 0
        not_found_count = 0
        already_accepted_count = 0
        
        for i, (friend_id, friend_invitations) in enumerate(invitations_by_friend.items()):
            # Take the first invitation (could be enhanced to choose "best" invitation)
            invitation = friend_invitations[0]
            
            friend = Person.find_by_id(invitation.friend_id)
            if friend is None:
                not_found_count += 1
                # Create rejection responses for ALL invitations to this friend
                for inv in friend_invitations:
                    response = LeisureResponse(invitation=inv, accepted=False)
                    self.pending_responses.append(response)
                continue
            
            # Check if friend already accepted an invitation this round
            if friend._accepted_invitation_this_round:
                accept = False
                already_accepted_count += 1
            else:
                # Decision logic
                if friend.subgroups.leisure is None:
                    if friend.busy: 
                        #Friend is not doing leisure but is working
                        accept = False
                    else:
                        # Friend wasn't doing leisure or working, easy accept
                        accept = True
                elif friend.id in potential_inviter_ids:
                    # Friend was planning to invite others, 50% chance to drop plans
                    accept = random.random() < 0.5
                else:
                    # Friend was doing solo leisure, 80% acceptance rate
                    accept = random.random() < 0.8
            
            if accept:
                accepted_count += 1
                friend._accepted_invitation_this_round = True
                
                # Remove from original leisure subgroup if they had one
                if friend.subgroups.leisure is not None:
                    # Check if friend is actually in the subgroup before attempting removal
                    original_subgroup = friend.subgroups.leisure
                    # Skip ExternalSubgroups - they don't have a 'people' attribute
                    if hasattr(original_subgroup, 'external') and original_subgroup.external:
                        # Just clear the reference for external subgroups
                        friend.subgroups.leisure = None
                    elif friend not in original_subgroup.people:
                        # This person was likely moved via MPI transfer already
                        # Clear the stale reference
                        friend.subgroups.leisure = None
                    else:
                        original_subgroup.remove(friend)
                
                # Mark for new assignment (will happen in apply_friend_assignments)
                friend._pending_friend_assignment = invitation
                
                # Create accepted response for the chosen invitation
                response = LeisureResponse(invitation=invitation, accepted=True)
                self.pending_responses.append(response)
                
                # Create rejection responses for all OTHER invitations to this friend
                for inv in friend_invitations[1:]:
                    response = LeisureResponse(invitation=inv, accepted=False)
                    self.pending_responses.append(response)
            else:
                rejected_count += 1
                
                # Create rejection responses for ALL invitations to this friend
                for inv in friend_invitations:
                    response = LeisureResponse(invitation=inv, accepted=False)
                    self.pending_responses.append(response)
            
    def exchange_responses(self) -> None:
        """
        Send all pending responses to appropriate ranks and receive responses from other ranks.
        """
        
        # Add MPI barrier to ensure all ranks reach this point
        mpi_comm.Barrier()
        
        # Organize responses by destination rank
        responses_by_rank = defaultdict(list)
        for response in self.pending_responses:
            if response.invitation.inviter_home_rank >= 0 and response.invitation.inviter_home_rank < mpi_size:
                responses_by_rank[response.invitation.inviter_home_rank].append(response)
            else:
                print(f"[Rank {mpi_rank}] exchange_responses: WARNING - Invalid rank {response.invitation.inviter_home_rank} for response")
                
        # Use non-blocking sends to avoid deadlock
        send_requests = []
        
        # Send responses to each rank using non-blocking sends
        for rank in range(mpi_size):
            if rank == mpi_rank:
                continue
            
            responses_for_rank = responses_by_rank.get(rank, [])
            
            req = mpi_comm.isend(responses_for_rank, dest=rank, tag=FRIEND_RESPONSE_TAG)
            send_requests.append(req)
        
        # Receive responses from each rank
        self.received_responses.clear()
        total_received = 0
        for rank in range(mpi_size):
            if rank == mpi_rank:
                continue
                        
            received = mpi_comm.recv(source=rank, tag=FRIEND_RESPONSE_TAG)
            self.received_responses.extend(received)
            total_received += len(received)
        
        # Wait for all sends to complete
        for i, req in enumerate(send_requests):
            req.wait()
            
    def apply_friend_assignments(self, world) -> None:
        """
        Apply friend assignments for people who accepted invitations.
        
        Parameters
        ----------
        world : World
            The simulation world containing all people
        """        
        friends_assigned = 0
        responses_processed = 0
        
        # Apply assignments for friends who accepted invitations on this rank
        cross_rank_groups = set()  # Track groups that received cross-rank friends
        
        for person in world.people:
            if person._pending_friend_assignment is not None:
                invitation = person._pending_friend_assignment
                
                # Create external subgroup pointing to inviter's venue
                external_group = ExternalGroup(
                    id=invitation.venue_id,
                    spec=invitation.activity_type,
                    domain_id=invitation.inviter_home_rank
                )
                
                external_subgroup = ExternalSubgroup(
                    group=external_group,
                    subgroup_type=invitation.subgroup_type
                )
                
                # Assign to person - this will flag them for MPI transfer
                person.subgroups.leisure = external_subgroup
                
                # Track this group for debugging - it received a cross-rank friend
                group_key = (invitation.activity_type, invitation.venue_id, invitation.inviter_home_rank)
                cross_rank_groups.add(group_key)
                
                friends_assigned += 1
        
        # Store debug info globally for simulator access
        if not hasattr(world, '_friend_invitation_debug'):
            world._friend_invitation_debug = {}
        world._friend_invitation_debug[mpi_rank] = {
            'cross_rank_groups': cross_rank_groups,
            'friends_assigned': friends_assigned
        }
        
        # Process responses for inviters on this rank
        for response in self.received_responses:
            responses_processed += 1
            if response.accepted:
                inviter = Person.find_by_id(response.invitation.inviter_id)
                if inviter is None:
                    print(f"[Rank {mpi_rank}] apply_friend_assignments: WARNING - Inviter {response.invitation.inviter_id} not found on this rank")
                else:
                    # Record temporary contact for cross-rank friend acceptance
                    if self.contact_manager is not None:
                        # Get current timestamp using cached simulator
                        current_timestamp = self._get_current_timestamp()
                        if current_timestamp is not None:
                            activity_type = response.invitation.activity_type
                            
                            # Record the leisure companion relationship for cross-rank friends
                            self.contact_manager.add_leisure_companion(
                                person_id=response.invitation.inviter_id,
                                companion_id=response.invitation.friend_id,
                                activity_type=activity_type,
                                timestamp=current_timestamp
                            )
            
    def person_chose_household(self, person):
        if person.residence.group.spec in ["care_home", "communal", "other", "student"]:
            return 0, 0
        
        all_household_members_ids = person.residence.group.get_all_registered_members_ids()

        housemates_to_invite = []

        for member_id in all_household_members_ids:
            housemates_to_invite.append(member_id)
        
        # Note: We don't record household member contacts here because they are already
        # tracked as permanent contacts in the contact manager. This method only handles
        # the logistics of household members joining leisure activities together.
        accepted, rejected = self._process_same_rank_invites(person, housemates_to_invite)
        return accepted, rejected
    
    def _are_household_members(self, person1: Person, person2: Person) -> bool:
        """
        Check if two people are members of the same household.
        
        Parameters
        ----------
        person1 : Person
            First person to check
        person2 : Person
            Second person to check
            
        Returns
        -------
        bool
            True if they are household members, False otherwise
        """
        if (person1.subgroups.residence is None or 
            person2.subgroups.residence is None):
            return False
            
        # Check if they live in the same residence
        return (person1.subgroups.residence.group.id == 
                person2.subgroups.residence.group.id and
                person1.subgroups.residence.group.spec == 
                person2.subgroups.residence.group.spec)

    def cleanup_temporary_attributes(self, world) -> None:
        """
        Clean up any temporary attributes that might remain on people.
        
        Parameters
        ----------
        world : World
            The simulation world containing all people
        """        
        cleaned_accepted = 0
        cleaned_pending = 0
        
        for person in world.people:
            if person._accepted_invitation_this_round:
                person._accepted_invitation_this_round = False
                cleaned_accepted += 1
            if person._pending_friend_assignment is not None:
                person._pending_friend_assignment = None
                cleaned_pending += 1    
    
    def _handle_external_inviter(self, person: Person) -> None:
        """
        Handle a person who wants to invite friends to an external venue.
        Does friend selection at home rank and sends pre-selected friend list.
        
        Parameters
        ----------
        person : Person
            External inviter who wants to invite friends
        """        
        # Do friend selection at home rank (where we have full social context)
        friends_to_invite = self._select_friends_to_invite(person)
        
        if not friends_to_invite:
            return
        
        # Look up where each selected friend lives
        selected_friends_with_ranks = {}
        for friend_id in friends_to_invite:
            friend_home_rank = self._get_friend_home_rank(person, friend_id)
            selected_friends_with_ranks[friend_id] = friend_home_rank
        
        # Create delegation with pre-selected friends
        delegation_info = {
            'inviter_id': person.id,
            'inviter_home_rank': person._home_rank,
            'venue_rank': person.subgroups.leisure.group.domain_id,
            'venue_id': person.subgroups.leisure.group.id,
            'activity_type': person.subgroups.leisure.spec,
            'subgroup_type': person.subgroups.leisure.subgroup_type,
            'selected_friends': selected_friends_with_ranks  # Pre-selected friends with their ranks
        }
        
        self.pending_delegations.append(delegation_info)
    
    def exchange_delegations(self) -> None:
        """
        Send delegation requests to venue ranks and receive delegations from other ranks.
        This allows venue ranks to handle invitations on behalf of external inviters.
        """        
        # Add MPI barrier to ensure all ranks reach this point
        mpi_comm.Barrier()
        
        # Organize delegations by destination venue rank
        delegations_by_rank = defaultdict(list)
        for delegation in self.pending_delegations:
            venue_rank = delegation['venue_rank']
            if venue_rank >= 0 and venue_rank < mpi_size:  # Valid rank
                delegations_by_rank[venue_rank].append(delegation)
            else:
                print(f"[Rank {mpi_rank}] exchange_delegations: WARNING - Invalid venue rank {venue_rank} for delegation")
                
        # Use non-blocking sends to avoid deadlock
        send_requests = []
        
        # Send delegations to each rank using non-blocking sends
        for rank in range(mpi_size):
            if rank == mpi_rank:
                continue
            
            delegations_for_rank = delegations_by_rank.get(rank, [])
            
            req = mpi_comm.isend(delegations_for_rank, dest=rank, tag=FRIEND_DELEGATION_TAG)
            send_requests.append(req)
                
        # Receive delegations from each rank
        self.received_delegations = []
        total_received = 0
        for rank in range(mpi_size):
            if rank == mpi_rank:
                continue
            
            received = mpi_comm.recv(source=rank, tag=FRIEND_DELEGATION_TAG)
            self.received_delegations.extend(received)
            total_received += len(received)
        
        # Wait for all sends to complete
        for i, req in enumerate(send_requests):
            req.wait()
            
    def process_delegations(self) -> None:
        """
        Process received delegations by routing pre-selected friends.
        Much simpler now - just route friends to appropriate ranks, no social decisions.
        """        
        delegated_invitations = 0
        local_friends_processed = 0
        
        for delegation in self.received_delegations:
            # Extract delegation information
            original_inviter_id = delegation['inviter_id']
            original_inviter_home_rank = delegation['inviter_home_rank']
            venue_id = delegation['venue_id']
            activity_type = delegation['activity_type']
            subgroup_type = delegation['subgroup_type']
            selected_friends = delegation['selected_friends']  # Dict of {friend_id: friend_home_rank}
                        
            # Route each pre-selected friend
            same_rank_friends = []
            cross_rank_invitations = []
            
            for friend_id, friend_home_rank in selected_friends.items():
                if friend_home_rank == mpi_rank:
                    # Friend is local to venue rank - process immediately
                    same_rank_friends.append(friend_id)
                else:
                    # Friend is on different rank - create cross-rank invitation
                    invitation = LeisureInvitation(
                        inviter_id=original_inviter_id,
                        inviter_home_rank=original_inviter_home_rank,
                        friend_id=friend_id,
                        friend_home_rank=friend_home_rank,
                        venue_id=venue_id,
                        activity_type=activity_type,
                        subgroup_type=subgroup_type
                    )
                    cross_rank_invitations.append(invitation)
            
            # Process same-rank friends immediately (they'll join the local venue)
            if same_rank_friends:
                accepted, rejected = self._process_delegated_same_rank_friends(
                    venue_id, activity_type, subgroup_type, same_rank_friends
                )
                local_friends_processed += len(same_rank_friends)
            
            # Add cross-rank invitations to pending list for normal MPI exchange
            self.pending_invitations.extend(cross_rank_invitations)
            delegated_invitations += len(cross_rank_invitations)
            
    def _process_delegated_same_rank_friends(self, venue_id: int, activity_type: str, 
                                           subgroup_type: int, friend_ids: List[int]) -> tuple:
        """
        Process same-rank friends for a delegated invitation.
        These friends will join the local venue directly.
        
        Parameters
        ----------
        venue_id : int
            ID of the venue
        activity_type : str
            Type of leisure activity
        subgroup_type : int
            Subgroup type within the venue
        friend_ids : List[int]
            List of friend IDs to invite
            
        Returns
        -------
        tuple
            (accepted_count, rejected_count)
        """        
        accepted_count = 0
        rejected_count = 0
        
        for friend_id in friend_ids:
            friend = Person.find_by_id(friend_id)
            if friend is None:
                rejected_count += 1
                continue
            
            # Check if friend already accepted an invitation this round
            if hasattr(friend, '_accepted_invitation_this_round') and friend._accepted_invitation_this_round:
                rejected_count += 1
                continue
            
            # Use same decision logic as normal invitations
            if friend.subgroups.leisure is None:
                if friend.busy:
                    #Friend is not doing leisure and is working
                    accept = False
                else:
                    accept = True  # Friend wasn't doing leisure, easy accept
            else:
                accept = random.random() < 0.8  # Friend was doing solo leisure, 80% acceptance rate
            
            if accept:
                accepted_count += 1
                friend._accepted_invitation_this_round = True
                
                # Remove from original leisure subgroup if they had one
                if friend.subgroups.leisure is not None:
                    original_subgroup = friend.subgroups.leisure
                    if hasattr(original_subgroup, 'external') and original_subgroup.external:
                        friend.subgroups.leisure = None
                    elif friend in original_subgroup.people:
                        original_subgroup.remove(friend)
                        friend.subgroups.leisure = None
                
            else:
                rejected_count += 1
        
        return accepted_count, rejected_count
