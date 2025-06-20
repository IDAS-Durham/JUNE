"""
Friendship Distributor Module

This module contains the `FriendshipDistributor` class and supporting functionality for
distributing friendships among a list of individuals based on configurable criteria such as
age tolerance, minimum and maximum number of friends, and activity groups.

Classes
-------
FriendshipDistributor
    Manages the creation and assignment of friendships based on various constraints.

"""

import logging
from random import choices, randint
import random
from time import perf_counter
import numpy as np

from june.demography.person import Person

logger = logging.getLogger("friendship_distributor")

class FriendshipDistributor:
    """
    Distributes friendships among a list of people based on configurable criteria.

    This class assigns friendships to individuals in the given list, ensuring
    constraints such as minimum and maximum number of friends, age tolerance,
    and minimum age for friendship are respected.

    Attributes
    ----------
    people : list
        List of Person instances to assign friendships to.
    min_friends : int
        Minimum number of friends an individual can have.
    max_friends : int
        Maximum number of friends an individual can have.
    age_tolerance : int
        Maximum allowed age difference between friends.
    min_friend_age : int
        Minimum age for a person to be eligible for friendship.
    """

    def __init__(self, people):
        """
        Initializes the FriendshipDistributor.

        Parameters
        ----------
        people : list
            List of Person instances.
        """
        min_friends = 1
        max_friends = 5
        age_tolerance = 5
        min_friend_age = 12
        self.people = people
        self.min_friends = min_friends
        self.max_friends = max_friends
        self.age_tolerance = age_tolerance
        self.min_friend_age = min_friend_age
        self.friendship_counts = {}  # Track friendships per super area

    def link_all_friends(self, super_areas):
        """
        Trigger the entire friendship linking process with optimized pre-filtering.
        """
        logger.info("Starting the friendship linking process...")
        
        # Initialize friendship counts once
        self.friendship_counts = {super_area.name: 0 for super_area in super_areas}
        
        # Pre-filter eligible people across the entire population
        logger.info("Pre-filtering eligible people...")
        
        # Use dictionaries for faster lookups
        eligible_people = {}  # person_id -> person
        age_ranges = {}       # person_id -> (min_age, max_age)
        
        # Optimize for specific activity types
        activity_by_type = {
            "company": {},    # company_id -> [people]
            "school": {},     # school_id -> [people]
            "university": {}, # university_id -> [people]
            "none": []        # people with no activity
        }
        
        area_people = {}      # area_id -> [list of eligible people]
        super_area_people = {}  # super_area_id -> [list of eligible people]
        
        # Single pass through all people to build all indexes
        total_people = 0
        eligible_count = 0
        
        # Process each super area efficiently
        for super_area in super_areas:
            super_id = id(super_area)
            super_area_people[super_id] = []
            
            # Process all areas in the super area
            for area in super_area.areas:
                area_id = id(area)
                area_people[area_id] = []
                total_people += len(area.people)
                
                # Process each person
                for person in area.people:
                    # Initialize friends dictionary if needed
                    if person.friends is None:
                        person.friends = {}
                    
                    # Skip ineligible people immediately
                    if person.age < self.min_friend_age:
                        continue
                    
                    eligible_count += 1
                    person_id = person.id
                    
                    # Store person reference and precalculate age range
                    eligible_people[person_id] = person
                    age_ranges[person_id] = (
                        max(self.min_friend_age, person.age - self.age_tolerance),
                        person.age + self.age_tolerance
                    )
                    
                    # Add to area and super area indexes
                    area_people[area_id].append(person)
                    super_area_people[super_id].append(person)
                    
                    # Classify by activity type
                    if person.subgroups.primary_activity is not None:
                        activity = getattr(person.subgroups.primary_activity, 'group', None)
                        if activity is not None:
                            # Get activity type and ID
                            activity_spec = getattr(activity, 'spec', None)
                            activity_id = id(activity)
                            
                            if activity_spec in activity_by_type:
                                if activity_id not in activity_by_type[activity_spec]:
                                    activity_by_type[activity_spec][activity_id] = []
                                activity_by_type[activity_spec][activity_id].append(person)
                            else:
                                # Default to no activity if spec not recognized
                                activity_by_type["none"].append(person)
                        else:
                            activity_by_type["none"].append(person)
                    else:
                        activity_by_type["none"].append(person)
        
        logger.info(f"Found {eligible_count} eligible people out of {total_people} total")
        
        # 1. Link friends in primary activity groups (highest priority) - optimized by activity type
        logger.info("Linking friends in primary activity groups...")
        activity_start = perf_counter()
        
        # Process schools first (typically smaller, more age-homogeneous groups)
        school_count = sum(len(group) for group in activity_by_type["school"].values())
        logger.info(f"Processing {len(activity_by_type['school'])} schools with {school_count} people")
        self._process_activity_type(
            activity_by_type["school"], 
            eligible_people, 
            age_ranges, 
            "activity",
            batch_size=50  # Smaller batch size for schools
        )
        
        # Process universities (medium-sized, somewhat age-homogeneous)
        uni_count = sum(len(group) for group in activity_by_type["university"].values())
        logger.info(f"Processing {len(activity_by_type['university'])} universities with {uni_count} people")
        self._process_activity_type(
            activity_by_type["university"], 
            eligible_people, 
            age_ranges, 
            "activity",
            batch_size=20  # Medium batch size for universities
        )
        
        # Process companies (can be very large and diverse)
        company_count = sum(len(group) for group in activity_by_type["company"].values())
        logger.info(f"Processing {len(activity_by_type['company'])} companies with {company_count} people")
        self._process_activity_type(
            activity_by_type["company"], 
            eligible_people, 
            age_ranges, 
            "activity",
            batch_size=10  # Smaller batch size for companies (which can be large)
        )
        
        activity_time = perf_counter() - activity_start
        logger.info(f"Activity linking completed in {activity_time:.2f} seconds")
        
        # 2. Link friends within areas for those who still need friends
        logger.info("Linking friends within areas...")
        area_start = perf_counter()
        
        # Filter people needing more friends after activity linking
        for area_id in area_people:
            # Skip empty areas
            if not area_people[area_id]:
                continue
            
            # Only process people who still need friends
            need_more_friends = [p for p in area_people[area_id] if len(p.friends) < self.max_friends]
            
            if need_more_friends:
                self._link_friends_directly(
                    people=need_more_friends,
                    eligible_people=eligible_people,
                    age_ranges=age_ranges,
                    context="area"
                )
        
        area_time = perf_counter() - area_start
        logger.info(f"Area linking completed in {area_time:.2f} seconds")
        
        # 3. Link friends within super areas for remaining cases
        logger.info("Linking friends within super areas...")
        super_area_start = perf_counter()
        
        for super_id in super_area_people:
            # Skip empty super areas
            if not super_area_people[super_id]:
                continue
            
            # Only process people who still need friends
            need_more_friends = [p for p in super_area_people[super_id] if len(p.friends) < self.max_friends]
            
            if len(need_more_friends) >= 2:  # Need at least 2 people to form friendships
                self._link_friends_directly(
                    people=need_more_friends,
                    eligible_people=eligible_people,
                    age_ranges=age_ranges,
                    context="super_area"
                )
        
        super_area_time = perf_counter() - super_area_start
        logger.info(f"Super area linking completed in {super_area_time:.2f} seconds")
        
        # Calculate friendship statistics
        total_time = activity_time + area_time + super_area_time
        total_friendships = sum(self.friendship_counts.values())
        
        logger.info(f"Friendship linking complete: {total_friendships} friendships created in {total_time:.2f} seconds")
        
        # Check for people without friends (sample for debugging)
        no_friends = self.find_people_without_friends(list(eligible_people.values()))
        if no_friends:
            logger.info(f"{len(no_friends)} eligible people have no friends.")
        else:
            logger.info("All eligible people have at least one friend.")


        # Debug Print: Sample Friendships Visualization
        logger.info("Visualizing a sample of friendships...")
        all_people = [
            person
            for super_area in super_areas
            for area in super_area.areas
            for person in area.people
        ]
        # Randomly select up to 10 people
        sample_people = random.sample(
            all_people,
            min(15, len(all_people))
        )

        def get_person_info(person):
            """
            Retrieve a formatted string with a person's details.
            """
            hobbies = ", ".join(person.hobbies) if person.hobbies else "None"
            return (
                f"ID {person.id} (Sex: {person.sex}, Age: {person.age}, "
                f"Primary Activity: {getattr(person.subgroups.primary_activity, 'group', None)}, "
                f"Area: {person.area.name if person.area else 'Unknown'}, "
                f"Super Area: {person.area.super_area.name if person.area and person.area.super_area else 'Unknown'}, "
                f"Hobbies: {hobbies})"
            )
        
        def get_friend_info(friend_id):
            """
            Retrieve a formatted string with a person's details.
            """
            friend=Person.find_by_id(friend_id)
            hobbies = ", ".join(friend.hobbies) if friend.hobbies else "None"
            return (
                f"ID {friend.id} (Sex: {friend.sex}, Age: {friend.age}, "
                f"Primary Activity: {getattr(friend.subgroups.primary_activity, 'group', None)}, "
                f"Area: {friend.area.name if person.area else 'Unknown'}, "
                f"Super Area: {friend.area.super_area.name if friend.area and friend.area.super_area else 'Unknown'}, "
                f"Hobbies: {hobbies})"
            )

        for person in sample_people:
            if person.friends:
                print(
                    f"Person {get_person_info(person)} is friends with:"
                )

                for friend_id, friend_data in person.friends.items():
                    # Handle both old format (just home_rank) and new format (dict)
                    if isinstance(friend_data, dict):
                        home_rank = friend_data.get("home_rank", 0)
                        friend_hobbies = friend_data.get("hobbies", [])
                        hobbies_str = ", ".join(friend_hobbies) if friend_hobbies else "None"
                        print(f"  - Friend {get_friend_info(friend_id)} (Home Rank: {home_rank}, Stored Hobbies: {hobbies_str})")
                    else:
                        # Old format - just home_rank
                        print(f"  - Friend {get_friend_info(friend_id)} (Home Rank: {friend_data})")

    
    def _process_activity_type(self, activity_groups, eligible_people, age_ranges, context, batch_size=20):
        """
        Process activities of a specific type.
        
        Parameters:
        -----------
        activity_groups : dict
            Dictionary mapping activity_id -> [list of people]
        eligible_people : dict
            Dictionary mapping person_id -> person
        age_ranges : dict
            Dictionary mapping person_id -> (min_age, max_age)
        context : str
            Context for friendship linking
        batch_size : int
            Number of groups to process in each batch
        """
        # Get sorted list of activity IDs, prioritizing by size (smallest first)
        activity_ids = sorted(
            activity_groups.keys(), 
            key=lambda x: len(activity_groups[x])
        )
        
        # Process in batches
        for batch_start in range(0, len(activity_ids), batch_size):
            batch_end = min(batch_start + batch_size, len(activity_ids))
            batch_activity_ids = activity_ids[batch_start:batch_end]
            
            for activity_id in batch_activity_ids:
                people = activity_groups[activity_id]
                
                # Skip groups with fewer than 2 people
                if len(people) < 2:
                    continue
                
                # For large groups, we'll need to be more selective
                if len(people) > 200:
                    # For large groups, pre-filter by age buckets
                    age_buckets = {}
                    for person in people:
                        age_bucket = person.age // 5  # Group ages in 5-year buckets
                        if age_bucket not in age_buckets:
                            age_buckets[age_bucket] = []
                        age_buckets[age_bucket].append(person)
                    
                    # Process each age bucket separately
                    for bucket in age_buckets.values():
                        if len(bucket) >= 2:  # Only process buckets with at least 2 people
                            self._link_friends_directly(
                                people=bucket,
                                eligible_people=eligible_people,
                                age_ranges=age_ranges,
                                context=context
                            )
                else:
                    # For smaller groups, process all at once
                    self._link_friends_directly(
                        people=people,
                        eligible_people=eligible_people,
                        age_ranges=age_ranges,
                        context=context
                    )
    

    def _link_friends_directly(self, people, eligible_people, age_ranges, context="generic"):
        """
        Optimized method to link friends using pre-calculated indexes.
        """
        # Create a cache for area-specific eligible people
        area_cache = {}  # area_id -> list of eligible people
        
        # Process people in batches for improved performance
        batch_size = min(1000, len(people))  # Adjust batch size based on memory constraints
        
        for batch_start in range(0, len(people), batch_size):
            batch_end = min(batch_start + batch_size, len(people))
            batch = people[batch_start:batch_end]
            
            for person in batch:
                # Skip if already at max friends
                remaining_slots = self.max_friends - len(person.friends)
                if remaining_slots <= 0:
                    continue
                    
                person_id = person.id
                min_age, max_age = age_ranges[person_id]
                
                # Find compatible potential friends based on context
                if context == "activity":
                    # For activity, we're already working with people in the same group
                    potential_friends = [
                        p for p in batch  # Only search within the current batch
                        if (p.id != person_id and 
                            p.id not in person.friends and
                            len(p.friends) < self.max_friends and
                            min_age <= p.age <= max_age)
                    ]
                elif context == "area":
                    # For area, use area-specific filtering with external cache
                    area = person.area
                    area_id = id(area)
                    
                    # Build cache for this area if not already done
                    if area_id not in area_cache:
                        area_cache[area_id] = [
                            p for p in area.people 
                            if p.id in eligible_people and p.age >= self.min_friend_age
                        ]
                    
                    potential_friends = [
                        p for p in area_cache[area_id]
                        if (p.id != person_id and 
                            p.id not in person.friends and
                            len(p.friends) < self.max_friends and
                            min_age <= p.age <= max_age)
                    ]
                elif context == "super_area":
                    # For super area, use more selective filtering
                    super_area = person.area.super_area
                    potential_friends = [
                        p for p in people  # people is already filtered to super area
                        if (p.id != person_id and 
                            p.id not in person.friends and
                            len(p.friends) < self.max_friends and
                            min_age <= p.age <= max_age and
                            p.area.super_area == super_area)
                    ]
                else:
                    # Generic context
                    potential_friends = [
                        p for p in people
                        if (p.id != person_id and 
                            p.id not in person.friends and
                            len(p.friends) < self.max_friends and
                            min_age <= p.age <= max_age)
                    ]
                    
                # Skip if no potential friends found
                n_potential = len(potential_friends)
                if n_potential == 0:
                    continue
                    
                # Calculate weights with numpy for speed
                weights = np.ones(n_potential, dtype=np.float32)
                
                for i, friend in enumerate(potential_friends):
                    # Prioritize connections based on multiple factors
                    
                    # 1. Super area match (highest priority)
                    if (person.area and friend.area and 
                        person.area.super_area == friend.area.super_area):
                        weights[i] *= 3.0
                    
                    # 2. Shared hobbies (significant boost)
                    if hasattr(person, "hobbies") and hasattr(friend, "hobbies"):
                        if person.hobbies and friend.hobbies:
                            shared_count = len(set(person.hobbies) & set(friend.hobbies))
                            if shared_count > 0:
                                weights[i] *= (1.5 + 0.5 * shared_count)
                            else:
                                weights[i] *= 0.7
                    
                    # 3. Work sector match (modest boost)
                    if person.sector == friend.sector and person.sector is not None:
                        weights[i] *= 1.2
                    
                    # 4. Age similarity (sliding scale)
                    age_diff = abs(person.age - friend.age)
                    weights[i] *= max(0.5, 1.0 - (age_diff / max(1, self.age_tolerance)))
                
                # Determine number of friends to add
                n_friends = min(
                    random.randint(1, remaining_slots),
                    n_potential
                )
                
                # Select friends using weighted probabilities
                if n_potential > 1:
                    probs = weights / np.sum(weights)
                    try:
                        # Try to use faster numpy selection when possible
                        indices = np.random.choice(
                            n_potential, 
                            size=n_friends,
                            replace=False,
                            p=probs
                        )
                        selected_friends = [potential_friends[i] for i in indices]
                    except ValueError:
                        # Fallback to standard random.choices if numpy fails
                        selected_friends = random.choices(
                            potential_friends,
                            weights=weights.tolist(),
                            k=min(n_friends, n_potential)
                        )
                else:
                    # Just one potential friend
                    selected_friends = potential_friends
                
                # Establish friendships (bidirectional)
                for friend in selected_friends:
                    # Get friend's hobbies for storage
                    friend_hobbies = getattr(friend, 'hobbies', []) or []
                    person_hobbies = getattr(person, 'hobbies', []) or []
                    
                    # Store friendship with home rank and hobbies
                    person.friends[friend.id] = {
                        "home_rank": 0,  # Default home rank to 0, will be updated later
                        "hobbies": friend_hobbies.copy()  # Store friend's hobbies
                    }
                    
                    if friend.friends is None:  # Safety check
                        friend.friends = {}
                    
                    friend.friends[person.id] = {
                        "home_rank": 0,  # Default home rank to 0, will be updated later
                        "hobbies": person_hobbies.copy()  # Store person's hobbies
                    }
                    
                    # Track friendship counts if needed
                    if hasattr(self, 'friendship_counts') and person.area and friend.area:
                        p_super = getattr(person.area, 'super_area', None)
                        f_super = getattr(friend.area, 'super_area', None)
                        
                        if p_super and p_super.name in self.friendship_counts:
                            self.friendship_counts[p_super.name] += 1
                        
                        if f_super and p_super != f_super and f_super.name in self.friendship_counts:
                            self.friendship_counts[f_super.name] += 1

    def find_people_without_friends(self, people):
        """
        Find and report individuals aged 12 or older without any friends.

        Parameters
        ----------
        people : list
            List of all people in the simulation.

        Returns
        -------
        list
            List of individuals aged 12 or older who have no friends.
        """
        no_friends = [
            person for person in people
            if (
                person.age >= self.min_friend_age)
                and
                (not person.friends or len(person.friends) == 0
            )
        ]
        return no_friends
