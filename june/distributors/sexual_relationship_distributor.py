import logging
import numpy as np
from typing import List, Dict, Set, Optional
from collections import defaultdict
import yaml
import pathlib

from june.demography import Person
from june.geography import Area, SuperArea

logger = logging.getLogger("sexual_relationship_distributor")

class SexualRelationshipDistributor:
    """
    Distributes sexual relationships, orientations, and related attributes to people
    in the population. This class handles:
    
    1. Assigning sexual orientations to individuals
    2. Managing existing couples (already living together)
    3. Creating new exclusive relationships for singles
    4. Creating non-exclusive relationships (non-monogamous partners)
    5. Adding the possibility of infidelity (non-consensual non-exclusivity)
    
    Relationships are stored in Person.sexual_partners with categories:
    - "exclusive": for monogamous partners
    - "non_exclusive": for non-monogamous partners
    
    The relationship_status attribute tracks:
    - type: "exclusive", "non_exclusive", "no_partner"
    - consensual: boolean (True for consensual, False for non-consensual/cheating)
    """
    
    def __init__(
        self,
        people: List[Person] = None,
        config_path: str = None,
        sexual_orientation_config: Dict = None,
        relationship_config: Dict = None,
        age_bins: List[int] = None,
        partner_limit_config: Dict = None,
        risk_profile_config: Dict = None,
        random_seed: int = None
    ):
        """
        Initialise the SexualRelationshipDistributor.
        
        Parameters
        ----------
        people:
            List of all people in the simulation (optional)
        config_path:
            Path to the YAML configuration file
        sexual_orientation_config:
            Dictionary containing probabilities of sexual orientations by gender and age
        relationship_config:
            Dictionary containing probabilities for different relationship types
        age_bins:
            List of age thresholds for binning purposes
        partner_limit_config:
            Dictionary containing limits on number of partners based on age, gender, and relationship type
        risk_profile_config:
            Dictionary containing risk profile configurations
        random_seed:
            Seed for random number generators to ensure reproducibility
        """
        self.people = people  # Store people for potential future use
        
        # Load configurations from YAML file
        self._load_configs(config_path)
        
        # Override with provided configs if specified
        if sexual_orientation_config:
            self.sexual_orientation_config = sexual_orientation_config
        if relationship_config:
            self.relationship_config = relationship_config
        if age_bins:
            self.age_bins = age_bins
        if partner_limit_config:
            self.partner_limit_config = partner_limit_config
        if risk_profile_config:
            self.risk_profile_config = risk_profile_config
            
        self.person_dict = {}
        if people:
            for person in people:
                self.person_dict[person.id] = person

        # Add caches
        self.compatibility_cache = {}  # (person1_id, person2_id) -> bool
        self.super_area_cache = {}  # (person1_id, person2_id) -> bool
        self.primary_activity_cache = {}  # (person1_id, person2_id) -> bool
        self.common_friends_cache = {}  # (person1_id, person2_id) -> bool
        self.age_bin_cache = {}  # person_id -> age_bin_string
                
        # Set random seed if provided for reproducibility
        if random_seed is not None:
            self.random_seed = random_seed
            np.random.seed(random_seed)
            logger.info(f"Using random seed {random_seed} for sexual relationship distribution")
        else:
            self.random_seed = None
        
        # Dictionary to track potential cheaters by ID
        self.potential_cheaters = set()
        
    def _load_configs(self, config_path=None):
        """
        Load configurations from YAML file.
        
        Parameters
        ----------
        config_path : str, optional
            Path to configuration file. If None, use default path.
        """
        try:
            # Set default path if not provided
            if config_path is None:
                base_path = pathlib.Path(__file__).parent.parent
                config_path = base_path / "configs" / "defaults" / "distributors" / "sexual_relationships_distributor.yaml"
            
            # Load YAML config
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            
            # Set configurations from file
            self.sexual_orientation_config = config.get("sexual_orientation_config", self._default_sexual_orientation_config())
            self.relationship_config = config.get("relationship_config", self._default_relationship_config())
            self.age_bins = config.get("age_bins", [18, 26, 36, 51, 65, 100])
            self.partner_limit_config = config.get("partner_limit_config", self._default_partner_limit_config())
            self.risk_profile_config = config.get("risk_profile_config", {})
            
            logger.info(f"Loaded sexual relationship distributor configuration from {config_path}")
        except (FileNotFoundError, yaml.YAMLError) as e:
            logger.warning(f"Could not load configuration from {config_path}: {e}")
            logger.warning("Using default configurations instead")
            
            # Use defaults if config file could not be loaded
            self.sexual_orientation_config = self._default_sexual_orientation_config()
            self.relationship_config = self._default_relationship_config()
            self.age_bins = [18, 26, 36, 51, 65, 100]
            self.partner_limit_config = self._default_partner_limit_config()
            self.risk_profile_config = {}
    
    @staticmethod
    def _default_sexual_orientation_config():
        """Default sexual orientation probabilities by gender."""
        return {
            "m": {"heterosexual": 0.95, "homosexual": 0.03, "bisexual": 0.02},
            "f": {"heterosexual": 0.93, "homosexual": 0.02, "bisexual": 0.05},
        }
    
    @staticmethod
    def _default_relationship_config():
        """Default relationship configuration with probabilities."""
        return {
            "relationship_probability": {
                "no_partner": 0.30,
                "exclusive": 0.60,
                "non_exclusive": 0.10
            },
            "cheating_probability": 0.30,  # Base probability of a person in exclusive relationship cheating
            "age_difference": {
                "18-25": [0, 3],    # Age range: [min_diff, max_diff]
                "26-35": [0, 5],
                "36-50": [0, 10],
                "51-64": [0, 15],
                "65+": [0, 15]
            },
            "location_bonus": 2.0,  # Multiplier for relationship probability if same super area
            "friends_bonus": 1.5,   # Multiplier for relationship probability if common friends
            "activity_bonus": 3.0   # Multiplier for non-exclusive relationship if same primary activity
        }
        
    @staticmethod
    def _default_partner_limit_config():
        """Default configuration for maximum number of partners based on age, gender, and relationship type."""
        return {
            # Default limits for non-exclusive relationships by age group and gender
            "non_exclusive": {
                "18-25": {
                    "m": 3,
                    "f": 3
                },
                "26-35": {
                    "m": 3,
                    "f": 2
                },
                "36-50": {
                    "m": 2,
                    "f": 2
                },
                "51-64": {
                    "m": 1,
                    "f": 1
                },
                "65+": {
                    "m": 1,
                    "f": 1
                }
            },
            # Cheating (non-consensual) limits are lower than non-exclusive
            "non_consensual": {
                "default": 1,  # Default for all age groups and genders
                # Exceptions to the default
                "18-25": {
                    "m": 2,
                    "f": 2
                },
                "26-35": {
                    "m": 1,
                    "f": 1
                }
            },
            # Exclusive relationships always have exactly 1 partner
            "exclusive": {
                "default": 1
            }
        }
    
    def _selective_cache_management(self, people: List[Person]) -> None:
        """
        Selectively manage caches rather than clearing them completely.
        Only remove entries for people who are no longer relevant.
        
        Parameters
        ----------
        people:
            List of currently relevant people
        """
        # Create a set of all current people IDs
        current_ids = {person.id for person in people}
        
        # Filter compatibility cache - now using frozenset keys
        self.compatibility_cache = {
            key: value for key, value in self.compatibility_cache.items()
            if all(person_id in current_ids for person_id in key)
        }
        
        # Similarly filter other caches
        self.super_area_cache = {
            key: value for key, value in self.super_area_cache.items()
            if key[0] in current_ids and key[1] in current_ids
        }
        
        self.primary_activity_cache = {
            key: value for key, value in self.primary_activity_cache.items()
            if key[0] in current_ids and key[1] in current_ids
        }
        
        self.common_friends_cache = {
            key: value for key, value in self.common_friends_cache.items()
            if key[0] in current_ids and key[1] in current_ids
        }
        
        # Keep valid age bin cache entries
        self.age_bin_cache = {
            key: value for key, value in self.age_bin_cache.items()
            if key in current_ids
        }
        
        # Pre-populate age bin cache for current people
        for person in people:
            if person.age >= 18 and person.id not in self.age_bin_cache:
                self.age_bin_cache[person.id] = self._get_age_bin(person)

    def _get_household_id(self, person: Person) -> Optional[str]:
        """Get the household ID for a person, if available."""
        if hasattr(person, "residence") and person.residence:
            if hasattr(person.residence, "group"):
                return getattr(person.residence.group, "id", None)
        return None

    def _get_primary_activity(self, person: Person) -> Optional[object]:
        """Get the primary activity for a person, if available."""
        if (hasattr(person, 'subgroups') and person.subgroups and 
            hasattr(person.subgroups, 'primary_activity')):
            return person.subgroups.primary_activity
        return None

    def _get_super_area(self, person: Person) -> Optional[object]:
        """Get the super area for a person, if available."""
        if (hasattr(person, 'area') and person.area and 
            hasattr(person.area, 'super_area')):
            return person.area.super_area
        return None

    def _get_friends(self, person: Person) -> Set[int]:
        """Get the set of friend IDs for a person, if available."""
        if hasattr(person, 'friends'):
            if isinstance(person.friends, (set, list)):
                return set(person.friends)
        return set()
    
    def _get_age_bin(self, person: Person) -> str:
        """
        Return the age bin category for a person.
        
        Parameters
        ----------
        person:
            The person to categorise
            
        Returns
        -------
        str:
            Age bin category as a string ("18-25", "26-35", etc.)
        """
        age = person.age
        
        # Check if person is already in cache
        if person.id in self.age_bin_cache:
            return self.age_bin_cache[person.id]
            
        # Calculate age bin
        if age < 26:
            age_bin = "18-25"
        elif age < 36:
            age_bin = "26-35"
        elif age < 51:
            age_bin = "36-50"
        elif age < 65:
            age_bin = "51-64"
        else:
            age_bin = "65+"
            
        # Store in cache
        self.age_bin_cache[person.id] = age_bin
        
        return age_bin
    
    def _filter_singles(self, people: List[Person]) -> List[Person]:
        """
        Filter out people who are already in relationships.
        
        Parameters
        ----------
        people:
            List of people to filter
            
        Returns
        -------
        list:
            List of single people (those without partners)
        """
        return [p for p in people if not p.has_sexual_partners]
    
    def _filter_by_relationship_type(self, people: List[Person], relationship_type: str, 
                                    consensual: Optional[bool] = None) -> List[Person]:
        """
        Filter people by their relationship type and consensual status.
        
        Parameters
        ----------
        people:
            List of people to filter
        relationship_type:
            Type of relationship to filter for ("exclusive", "non_exclusive", "no_partner")
        consensual:
            If provided, filter by consensual status as well
            
        Returns
        -------
        list:
            Filtered list of people
        """
        if consensual is None:
            # Filter only by relationship type
            return [p for p in people if p.relationship_status.get("type") == relationship_type]
        else:
            # Filter by relationship type and consensual status
            return [p for p in people if p.relationship_status.get("type") == relationship_type and 
                                        p.relationship_status.get("consensual") == consensual]
        
    def _initialise_relationship_status(self, person: Person) -> None:
        """
        Initialise relationship status for a person if not already set.
        
        Parameters
        ----------
        person:
            Person to initialise
        """
        if not hasattr(person, "relationship_status") or not person.relationship_status:
            person.relationship_status = {"type": "no_partner", "consensual": True}
            
        if not hasattr(person, "sexual_partners") or not person.sexual_partners:
            person.sexual_partners = {"exclusive": set(), "non_exclusive": set()}
    
    def distribute_sexual_relationships(self, super_areas: List[SuperArea]) -> None:
        """
        Main method to distribute sexual relationships across all super areas.
        
        Parameters
        ----------
        super_areas:
            List of super areas to process
        """
        logger.info("Distributing sexual relationships and orientations")
        
        # Build a complete person dictionary for the whole simulation
        self.person_dict = {}
        for super_area in super_areas:
            for area in super_area.areas:
                for person in area.people:
                    self.person_dict[person.id] = person

        # Track total areas processed for logging
        total_areas = sum(len(super_area.areas) for super_area in super_areas)
        areas_processed = 0
        
        # Process each super area and its contained areas
        for super_area in super_areas:
            for area in super_area.areas:
                self.distribute_area_relationships(area)
                areas_processed += 1
                
                # Log progress periodically
                if areas_processed % 1000 == 0:
                    logger.info(f"Processed sexual relationships for {areas_processed} areas of {total_areas}")
        
        logger.info("Completed sexual relationship distribution")
        
        # Print some statistics for verification
        self._print_relationship_statistics(super_areas)
    
    def distribute_area_relationships(self, area: Area) -> None:
        """
        Process relationships for a single area.
        Uses Person helper methods where appropriate.
        """
        # Selectively manage caches for this area
        self._selective_cache_management(area.people)

        # Gather all people in the area
        people = area.people
        adults = [p for p in people if p.age >= 18]

        # Pre-compute age bins for all adults
        for person in adults:
            self.age_bin_cache[person.id] = self._get_age_bin(person)
        
        # Initialise relationship status for all adults
        for person in adults:
            self._initialise_relationship_status(person)
        
        # 1. Identify people already in relationships vs singles
        singles = self._filter_by_relationship_type(adults, "no_partner")
        already_coupled = [p for p in adults if p not in singles]
        
        # Process existing household partnerships
        household_partners = defaultdict(set)
        for person in already_coupled:
            # Process existing exclusive partners
            for partner_id in person.get_partners("exclusive"):
                # Record this relationship in household_partners
                household_partners[person.id].add(partner_id)
                household_partners[partner_id].add(person.id)
                
                # Only process once per pair to avoid duplicate work
                if partner_id > person.id:
                    partner = self.person_dict.get(partner_id)
                    if partner:
                        self._assign_orientation_for_existing_couple(person, partner_id)
                    
        # 2. Assign sexual orientations to all adults
        for person in adults:
            # Only assign if not already set
            if not hasattr(person, "sexual_orientation") or person.sexual_orientation is None:
                self._assign_sexual_orientation(person)

        # 3. Create exclusive relationships among singles based on probability
        self._create_exclusive_relationships(singles, area, household_partners)
        
        # 4. Handle non-exclusive relationships (casual partners and cheating)
        self._create_non_exclusive_relationships(adults, household_partners)

        # 5. Assign risk profiles to all adults
        self._assign_risk_profiles(adults)
    
    def _assign_sexual_orientation(self, person: Person) -> None:
        """
        Assign sexual orientation to a person based on configured probabilities.
        
        Parameters
        ----------
        person:
            Person to assign orientation to
        """
        orientation_probs = self.sexual_orientation_config.get(person.sex, self.sexual_orientation_config["m"])
        orientations = list(orientation_probs.keys())
        probabilities = list(orientation_probs.values())
        
        # Normalise probabilities if they don't sum to 1
        total_prob = sum(probabilities)
        if total_prob != 1.0:
            probabilities = [p/total_prob for p in probabilities]
        
        # Assign orientation
        person.sexual_orientation = np.random.choice(orientations, p=probabilities)
        
    def _assign_orientation_for_existing_couple(self, person: Person, partner_id: int) -> None:
        """
        Assign compatible sexual orientations to people in existing relationships.
        For now, all previously existing couples assigned in household distributor are M/F.
        
        Possible combinations:
        - m: heterosexual, f: heterosexual
        - m: bisexual, f: heterosexual
        - m: bisexual, f: bisexual
        - m: heterosexual, f: bisexual
        
        Parameters
        ----------
        person:
            Person in the relationship
        partner_id:
            ID of the partner
        """
        # Find the partner
        partner = self.person_dict.get(partner_id)
        if not partner:
            return
        
        # Set orientation probabilities based on configuration
        m_probs = self.sexual_orientation_config["m"]
        f_probs = self.sexual_orientation_config["f"]
        
        if person.sex == "m" and partner.sex == "f":
            # Male in relationship with female
            # Male can be heterosexual or bisexual
            # Female can be heterosexual or bisexual
            m_choices = ["heterosexual", "bisexual"]
            m_weights = [m_probs["heterosexual"], m_probs["bisexual"]]
            total_m_weight = sum(m_weights)
            m_weights = [w/total_m_weight for w in m_weights]
            
            f_choices = ["heterosexual", "bisexual"]
            f_weights = [f_probs["heterosexual"], f_probs["bisexual"]]
            total_f_weight = sum(f_weights)
            f_weights = [w/total_f_weight for w in f_weights]

            person.sexual_orientation = np.random.choice(m_choices, p=m_weights)
            partner.sexual_orientation = np.random.choice(f_choices, p=f_weights)
                
        elif person.sex == "f" and partner.sex == "m":
            # Female in relationship with male
            # Female can be heterosexual or bisexual
            # Male can be heterosexual or bisexual
            f_choices = ["heterosexual", "bisexual"]
            f_weights = [f_probs["heterosexual"], f_probs["bisexual"]]
            total_f_weight = sum(f_weights)
            f_weights = [w/total_f_weight for w in f_weights]
            
            m_choices = ["heterosexual", "bisexual"]
            m_weights = [m_probs["heterosexual"], m_probs["bisexual"]]
            total_m_weight = sum(m_weights)
            m_weights = [w/total_m_weight for w in m_weights]
            
            person.sexual_orientation = np.random.choice(f_choices, p=f_weights)
            partner.sexual_orientation = np.random.choice(m_choices, p=m_weights)

    def _is_compatible_orientation(self, person1: Person, person2: Person) -> bool:
        """
        Check if two people have compatible sexual orientations.
        Uses frozenset for cache keys to avoid checking both permutations.
        """
        # Use frozenset as cache key to avoid checking both permutations
        cache_key = frozenset([person1.id, person2.id])
        
        if cache_key in self.compatibility_cache:
            return self.compatibility_cache[cache_key]
        
        # If not in cache, calculate compatibility using optimised checks
        # Avoid redundant calculations by using early returns
        
        # Fast-path for bisexual people (always compatible with everyone)
        if person1.sexual_orientation == "bisexual" and person2.sexual_orientation == "bisexual":
            self.compatibility_cache[cache_key] = True
            return True
            
        # Check heterosexual compatibility (different sexes)
        if person1.sexual_orientation == "heterosexual" and person2.sexual_orientation == "heterosexual":
            compatible = person1.sex != person2.sex
            self.compatibility_cache[cache_key] = compatible
            return compatible
            
        # Check homosexual compatibility (same sex)
        if person1.sexual_orientation == "homosexual" and person2.sexual_orientation == "homosexual":
            compatible = person1.sex == person2.sex
            self.compatibility_cache[cache_key] = compatible
            return compatible
        
        # Mixed orientations require more detailed checks
        p1_to_p2 = False
        p2_to_p1 = False
        
        # First person's attraction to second
        if person1.sexual_orientation == "heterosexual" and person1.sex != person2.sex:
            p1_to_p2 = True
        elif person1.sexual_orientation == "homosexual" and person1.sex == person2.sex:
            p1_to_p2 = True
        elif person1.sexual_orientation == "bisexual":
            p1_to_p2 = True
            
        # Second person's attraction to first
        if person2.sexual_orientation == "heterosexual" and person2.sex != person1.sex:
            p2_to_p1 = True
        elif person2.sexual_orientation == "homosexual" and person2.sex == person1.sex:
            p2_to_p1 = True
        elif person2.sexual_orientation == "bisexual":
            p2_to_p1 = True
            
        # Both need to be attracted to each other
        compatible = p1_to_p2 and p2_to_p1
        
        # Store in cache
        self.compatibility_cache[cache_key] = compatible
        
        return compatible

    
    def _get_age_appropriate_partners(self, person: Person, candidates: List[Person]) -> List[Person]:
        """
        Filter candidates to those with age-appropriate differences based on person's age.
        
        Parameters
        ----------
        person:
            The person seeking partners
        candidates:
            List of potential partners to filter
            
        Returns
        -------
        list:
            List of candidates with age-appropriate differences
        """
        # Get age bin from cache
        age_bin = self.age_bin_cache.get(person.id)
        
        # Determine age preference based on age bin
        age_diff_range = self.relationship_config["age_difference"][age_bin]
        min_diff, max_diff = age_diff_range
        
        # Filter candidates based on age difference
        appropriate_candidates = []
        for candidate in candidates:
            age_diff = abs(candidate.age - person.age)
            if min_diff <= age_diff <= max_diff:
                appropriate_candidates.append(candidate)
                
        # If no appropriate candidates, return all candidates
        return appropriate_candidates or candidates
    
    def _get_cheating_probability(self, person: Person) -> float:
        """
        Return age-adjusted cheating probability.
        
        Parameters
        ----------
        person:
            Person to calculate probability for
            
        Returns
        -------
        float:
            Age-adjusted cheating probability
        """
        base_probability = self.relationship_config["cheating_probability"]
        age_bin = self.age_bin_cache.get(person.id)
        
        if age_bin == "18-25":
            # Younger people more likely to cheat
            return min(base_probability * 1.5, 1.0)
        elif age_bin == "26-35" or age_bin == "36-50":
            # Middle-aged people at base rate
            return base_probability
        elif age_bin == "51-64":
            # Older adults less likely to cheat
            return base_probability * 0.7
        else:  # 65+
            # Elderly people much less likely to cheat
            return base_probability * 0.3
    
    def _get_non_exclusive_probability(self, person: Person) -> float:
        """
        Return age-adjusted non-exclusive relationship probability.
        
        Parameters
        ----------
        person:
            Person to calculate probability for
            
        Returns
        -------
        float:
            Age-adjusted non-exclusive probability
        """
        base_probability = self.relationship_config["relationship_probability"]["non_exclusive"]
        age = person.age
        
        if age < 30:
            # Younger people more open to non-exclusive relationships
            return min(base_probability * 2.0, 1.0)
        elif age < 50:
            # Middle-aged people at base rate
            return base_probability
        elif age < 65:
            # Older adults less likely
            return base_probability * 0.5
        else:
            # Elderly people much less likely
            return base_probability * 0.2


    def _are_from_same_household(self, person1: Person, person2: Person) -> bool:
        """
        Check if two people are from the same household.
        
        Parameters
        ----------
        person1:
            First person
        person2:
            Second person
            
        Returns
        -------
        bool:
            True if from same household, False otherwise
        """
        household1 = self._get_household_id(person1)
        household2 = self._get_household_id(person2)
        
        if household1 and household2:
            return household1 == household2
        return False
    
    def _are_from_same_super_area(self, person1: Person, person2: Person) -> bool:
        """
        Check if two people are from the same super area.
        
        Parameters
        ----------
        person1:
            First person
        person2:
            Second person
            
        Returns
        -------
        bool:
            True if from same super area, False otherwise
        """
        cache_key = (person1.id, person2.id)
        reverse_key = (person2.id, person1.id)
        
        if cache_key in self.super_area_cache:
            return self.super_area_cache[cache_key]
        if reverse_key in self.super_area_cache:
            return self.super_area_cache[reverse_key]
            
        # Calculate result
        result = False
        super_area1 = self._get_super_area(person1)
        super_area2 = self._get_super_area(person2)
        
        if super_area1 and super_area2:
            result = super_area1.name == super_area2.name
        
        # Store in cache
        self.super_area_cache[cache_key] = result
        return result
        
    def _have_same_primary_activity(self, person1: Person, person2: Person) -> bool:
        """
        Check if two people share the same primary activity (workplace, school, etc.)
        
        Parameters
        ----------
        person1:
            First person
        person2:
            Second person
            
        Returns
        -------
        bool:
            True if they share the same primary activity, False otherwise
        """
        cache_key = (person1.id, person2.id)
        reverse_key = (person2.id, person1.id)
        
        if cache_key in self.primary_activity_cache:
            return self.primary_activity_cache[cache_key]
        if reverse_key in self.primary_activity_cache:
            return self.primary_activity_cache[reverse_key]
        
        # If not in cache, calculate the result
        activity1 = self._get_primary_activity(person1)
        activity2 = self._get_primary_activity(person2)
        
        result = False
        if activity1 and activity2:
            result = activity1 == activity2
        
        # Store in cache
        self.primary_activity_cache[cache_key] = result
        
        return result
    
    def _have_common_friends(self, person1: Person, person2: Person) -> bool:
        """
        Check if two people have common friends.
        
        Parameters
        ----------
        person1:
            First person
        person2:
            Second person
            
        Returns
        -------
        bool:
            True if they have common friends, False otherwise
        """
        # Check if both have friend attributes
        cache_key = (person1.id, person2.id)
        reverse_key = (person2.id, person1.id)
        
        if cache_key in self.common_friends_cache:
            return self.common_friends_cache[cache_key]
        if reverse_key in self.common_friends_cache:
            return self.common_friends_cache[reverse_key]
        
        # If not in cache, calculate the result
        friends1 = self._get_friends(person1)
        friends2 = self._get_friends(person2)
        
        result = len(friends1.intersection(friends2)) > 0
        
        # Store in cache
        self.common_friends_cache[cache_key] = result
        
        return result
    
    def _find_compatible_partners(self, 
                                person: Person, 
                                candidates: List[Person], 
                                exclude_household: bool = True,
                                household_partners: Dict[int, Set[int]] = None) -> List[Person]:
        """
        Find compatible partners based on orientation, household status, etc.
        
        Parameters
        ----------
        person:
            Person looking for partners
        candidates:
            List of potential partners
        exclude_household:
            Whether to exclude people from the same household
        household_partners:
            Dictionary of existing household partnerships
            
        Returns
        -------
        list:
            List of compatible partners
        """
        # Find compatible partners by orientation
        orientation_compatible = [
            p for p in candidates 
            if p.id != person.id and self._is_compatible_orientation(person, p)
        ]
        
        if not orientation_compatible:
            return []
        
        # If we're not considering household status, return all orientation-compatible
        if not exclude_household:
            return orientation_compatible
        
        # Handle household filtering
        same_household_ok = []
        non_household = []
        
        # If we have household_partners, check it
        if household_partners is None:
            household_partners = {}
        
        for p in orientation_compatible:
            # Check if they're already set as partners from household distributor
            if p.id in household_partners.get(person.id, set()):
                # They're already partners from household distributor, so it's OK
                same_household_ok.append(p)
            elif not self._are_from_same_household(person, p):
                # Not from same household, so it's OK
                non_household.append(p)
        
        # Prioritise based on relationship context
        # For most relationships, prioritise non-household members
        return non_household + same_household_ok
    
    def _select_partner_by_score(self, 
                                person: Person, 
                                candidates: List[Person], 
                                is_non_exclusive: bool = False) -> Optional[Person]:
        """
        Select a partner from candidates using compatibility scoring with efficient weighted sampling.
        
        Parameters
        ----------
        person:
            Person seeking partners
        candidates:
            List of compatible candidates
        is_non_exclusive:
            Whether this is for a non-exclusive relationship
            
        Returns
        -------
        Person or None:
            Selected partner or None if no suitable partner found
        """
        if not candidates:
            return None
        
        # Age-appropriate filtering
        age_appropriate = self._get_age_appropriate_partners(person, candidates)
        
        if not age_appropriate:
            age_appropriate = candidates
        
        # Calculate compatibility scores without sorting
        weights = np.array([self._calculate_compatibility_score(person, candidate, is_non_exclusive=is_non_exclusive) 
                            for candidate in age_appropriate])
        
        # Check if we have valid weights
        total_weight = np.sum(weights)
        
        if total_weight > 0:
            # Normalise weights to probabilities and perform weighted selection directly
            probabilities = weights / total_weight
            selected_index = np.random.choice(len(age_appropriate), p=probabilities)
            return age_appropriate[selected_index]
        elif age_appropriate:
            # If all weights are zero but we have candidates, choose randomly
            return np.random.choice(age_appropriate)
        else:
            # No suitable candidates
            return None
    
    def _calculate_compatibility_score(self, person1: Person, person2: Person, is_non_exclusive: bool = False) -> float:
        """
        Calculate a compatibility score between two people based on various factors.
        
        Parameters
        ----------
        person1:
            First person
        person2:
            Second person
        is_non_exclusive:
            Whether this is for a non-exclusive relationship (applies primary activity bonus)
            
        Returns
        -------
        float:
            Compatibility score (higher is more compatible)
        """
        score = 1.0
        
        # Age difference factor (closer ages get higher scores)
        age_diff = abs(person1.age - person2.age)
        if age_diff < 5:
            score *= 1.5
        elif age_diff < 10:
            score *= 1.2
        
        # Same super area bonus
        if self._are_from_same_super_area(person1, person2):
            score *= self.relationship_config["location_bonus"]
        
        # Common friends bonus
        if self._have_common_friends(person1, person2):
            score *= self.relationship_config["friends_bonus"]
        
        # Apply primary activity bonus for non-exclusive relationships
        if is_non_exclusive and self._have_same_primary_activity(person1, person2):
            score *= self.relationship_config["activity_bonus"]
        
        return score
    
    def _calculate_cheating_probability(self, person: Person) -> float:
        """
        Calculate the probability that a person will cheat, based on their age and other factors.
        
        Parameters
        ----------
        person:
            The person to calculate probability for
            
        Returns
        -------
        float:
            Probability of cheating (0.0 to 1.0)
        """
        base_probability = self.relationship_config["cheating_probability"]
        age = person.age
        
        # Age-based adjustment
        if age < 25:
            # Younger people more likely to cheat
            cheating_prob = base_probability * 1.5
        elif age < 35:
            # Young adults slightly more likely
            cheating_prob = base_probability * 1.2
        elif age < 50:
            # Middle-aged at base rate
            cheating_prob = base_probability
        elif age < 65:
            # Older adults less likely
            cheating_prob = base_probability * 0.7
        else:  # 65+
            # Elderly much less likely
            cheating_prob = base_probability * 0.3
        
        # Apply gender adjustment if in risk profile config
        if hasattr(self, 'risk_profile_config') and 'gender_risk_factors' in self.risk_profile_config:
            gender_factors = self.risk_profile_config['gender_risk_factors'].get(person.sex, {})
            cheating_adjustment = gender_factors.get('cheating_adjustment', 0.0)
            cheating_prob += cheating_adjustment
        
        # Cap the probability between 0 and 1
        return max(0.0, min(1.0, cheating_prob))
    
    def _create_exclusive_relationships(self, singles: List[Person], area: Area, household_partners: Dict[int, Set[int]]) -> None:
        """
        Create exclusive relationships among singles.
        Uses Person helper methods where appropriate.
        """
        # Filter singles who should have exclusive relationships
        np.random.shuffle(singles)
        
        available_singles = []
        for person in singles:
            # Skip if the person shouldn't have an exclusive relationship 
            relationship_probs = self.relationship_config["relationship_probability"]
            exclusive_vs_no_partner = relationship_probs["exclusive"] / (relationship_probs["exclusive"] + relationship_probs["no_partner"])
            
            if np.random.random() < exclusive_vs_no_partner:
                available_singles.append(person)
        
        # Group by age bins for better matching
        age_binned_singles = defaultdict(list)
        for person in available_singles:
            bin_idx = 0
            for i, threshold in enumerate(self.age_bins):
                if person.age < threshold:
                    bin_idx = i
                    break
            
            age_binned_singles[bin_idx].append(person)
        
        # Process each age bin
        matched = set()
        for bin_idx, bin_singles in age_binned_singles.items():
            remaining = [p for p in bin_singles if p.id not in matched]
            
            while len(remaining) >= 2:
                person1 = remaining.pop(0)
                
                # Find compatible partners
                compatible_partners = self._find_compatible_partners(
                    person1, 
                    remaining, 
                    exclude_household=True, 
                    household_partners=household_partners
                )
                
                if not compatible_partners:
                    continue
                
                # Filter by age-appropriateness
                age_appropriate = self._get_age_appropriate_partners(person1, compatible_partners)
                
                if not age_appropriate:
                    age_appropriate = compatible_partners
                
                # Select partner using compatibility scoring
                person2 = self._select_partner_by_score(person1, age_appropriate)
                
                if not person2:
                    continue
                    
                # Remove the selected partner from remaining
                remaining.remove(person2)
                
                # Create exclusive relationship
                self._create_relationship(person1, person2, "exclusive")
                
                # Determine potential cheaters
                if np.random.random() < self._get_cheating_probability(person1):
                    self.potential_cheaters.add(person1.id)
                if np.random.random() < self._get_cheating_probability(person2):
                    self.potential_cheaters.add(person2.id)
                
                # Mark as matched
                matched.add(person1.id)
                matched.add(person2.id)
    
    def _create_non_exclusive_relationships(self, people: List[Person], household_partners: Dict[int, Set[int]]) -> None:
        """
        Create non-exclusive relationships, including:
        1. People who prefer non-exclusive relationships
        2. People in exclusive relationships who cheat
        
        Parameters
        ----------
        people:
            List of all people in the area
        household_partners:
            Dictionary mapping person IDs to sets of partner IDs from household distributor
        """
        # Filter adults
        adults = [p for p in people if p.age >= 18]
        
        # Get singles who could become non-exclusive relationship seekers
        singles = self._filter_by_relationship_type(adults, "no_partner")
        
        # Get potential cheaters (people in exclusive relationships who might cheat)
        exclusive_people = self._filter_by_relationship_type(adults, "exclusive", True)
        potential_cheaters = [p for p in exclusive_people if p.id in self.potential_cheaters]
        
        # Identify people who want non-exclusive relationships
        non_exclusive_seekers = []
        for person in singles:
            # Decide if this single person wants non-exclusive relationships
            # Use age-adjusted probability
            non_exclusive_prob = self._get_non_exclusive_probability(person)
            
            # Calculate adjusted probability relative to no_partner
            rel_probs = self.relationship_config["relationship_probability"]
            no_partner_prob = rel_probs["no_partner"]
            
            # Calculate probability of non-exclusive vs no_partner
            non_exclusive_vs_no_partner = non_exclusive_prob / (non_exclusive_prob + no_partner_prob)
            
            if np.random.random() < non_exclusive_vs_no_partner:
                person.set_relationship_status("non_exclusive", True)
                non_exclusive_seekers.append(person)
        
        # Create non-exclusive relationships between non_exclusive seekers
        self._create_consensual_non_exclusive_relationships(non_exclusive_seekers, household_partners)
        
        # Create cheating relationships for potential cheaters
        self._create_cheating_relationships(potential_cheaters, non_exclusive_seekers, household_partners)
    
    def _get_max_partners(self, person: Person, relationship_context: str = "non_exclusive") -> int:
        """
        Determine the maximum number of partners a person can have based on their age, gender,
        and relationship context.
        
        Parameters
        ----------
        person:
            The person to determine max partners for
        relationship_context:
            The relationship context ("exclusive", "non_exclusive", or "non_consensual")
            
        Returns
        -------
        int:
            Maximum number of allowed partners for this person in this context
        """
        # Default limit if configuration doesn't specify
        default_limit = 1
        
        # For exclusive relationships, always return 1
        if relationship_context == "exclusive":
            return self.partner_limit_config["exclusive"]["default"]
        
        # Get age group from cache
        age_group = self.age_bin_cache.get(person.id)
        
        # Get gender
        gender = person.sex  # "m" or "f"
        
        # For non-consensual (cheating), check specific config or use default
        if relationship_context == "non_consensual":
            # Check if specific configuration exists for this age group and gender
            if age_group in self.partner_limit_config["non_consensual"]:
                if gender in self.partner_limit_config["non_consensual"][age_group]:
                    return self.partner_limit_config["non_consensual"][age_group][gender]
            
            # If no specific config, return default for non-consensual
            return self.partner_limit_config["non_consensual"]["default"]
        
        # For non-exclusive, look up appropriate limit
        if age_group in self.partner_limit_config["non_exclusive"]:
            if gender in self.partner_limit_config["non_exclusive"][age_group]:
                return self.partner_limit_config["non_exclusive"][age_group][gender]
        
        # If we couldn't find a specific limit, return default
        return default_limit
    
    def _create_consensual_non_exclusive_relationships(self, non_exclusive_seekers: List[Person], household_partners: Dict[int, Set[int]]) -> None:
        """
        Create non-exclusive relationships between people seeking non-exclusive relationships.
        These are consensual non-monogamous relationships where both parties agree
        to the arrangement.
        
        Parameters
        ----------
        non_exclusive_seekers:
            List of people seeking non-exclusive relationships
        household_partners:
            Dictionary mapping person IDs to sets of partner IDs from household distributor
        """
        # Randomise
        np.random.shuffle(non_exclusive_seekers)
        
        # Track current partner counts for all people to enforce limits
        partner_counts = {}
        for person in non_exclusive_seekers:
            if hasattr(person, "sexual_partners") and "non_exclusive" in person.sexual_partners:
                partner_counts[person.id] = len(person.sexual_partners["non_exclusive"])
            else:
                partner_counts[person.id] = 0
        
        # Each person might have multiple partners
        for i, person in enumerate(non_exclusive_seekers):
            # Skip if person already processed or removed
            if person.id not in partner_counts:
                continue
                
            # Skip if person already at or over their limit
            current_partner_count = partner_counts[person.id]
            max_partners = self._get_max_partners(person, "non_exclusive")
            
            if current_partner_count >= max_partners:
                continue
            
            # Determine remaining partners allowed
            remaining_partners = max_partners - current_partner_count
            
            # Determine number of partners to add (limited by remaining_partners)
            # Use probabilities that favor fewer partners
            if remaining_partners == 1:
                num_partners = 1
            elif remaining_partners == 2:
                num_partners = np.random.choice([1, 2], p=[0.6, 0.4])
            elif remaining_partners == 3:
                num_partners = np.random.choice([1, 2, 3], p=[0.5, 0.3, 0.2])
            elif remaining_partners == 4:
                num_partners = np.random.choice([1, 2, 3, 4], p=[0.4, 0.3, 0.2, 0.1])
            else:
                num_partners = np.random.choice(range(1, remaining_partners + 1), p=None)  # Uniform distribution
            
            # Find potential partners with compatible orientation
            orientation_compatible = [
                p for p in non_exclusive_seekers 
                if p.id != person.id and self._is_compatible_orientation(person, p)
            ]
            
            # Filter out people from the same household (unless already set as partners)
            same_household_ok = []
            non_household = []
            
            for p in orientation_compatible:
                # Check if they're already set as partners from household distributor
                if p.id in household_partners.get(person.id, set()):
                    # They're already partners from household distributor, so it's OK
                    same_household_ok.append(p)
                elif not self._are_from_same_household(person, p):
                    # Not from same household, so it's OK
                    non_household.append(p)
            
            # Prioritise non-household partners for non-exclusive relationships,
            # but include pre-existing household partners if needed
            candidates = non_household + same_household_ok
            
            if not candidates:
                continue
            
            # Filter by age-appropriateness
            age_appropriate = self._get_age_appropriate_partners(person, candidates)
            
            if not age_appropriate:
                age_appropriate = candidates
            
            # Filter out candidates who have already reached their maximum partners
            valid_candidates = []
            for candidate in age_appropriate:
                if candidate.id in partner_counts:
                    candidate_max = self._get_max_partners(candidate, "non_exclusive")
                    if partner_counts[candidate.id] < candidate_max:
                        valid_candidates.append(candidate)
                else:
                    valid_candidates.append(candidate)
            
            if not valid_candidates:
                continue
            
            # Score potential partners by compatibility - include activity bonus for non-exclusive
            scored_candidates = [(p, self._calculate_compatibility_score(person, p, is_non_exclusive=True)) 
                               for p in valid_candidates]
            
            # Sort by compatibility score (higher scores first)
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Limit to actual number available
            num_partners = min(num_partners, len(scored_candidates))
            
            # Create relationships with top-scored partners
            for j in range(num_partners):
                if j < len(scored_candidates):
                    partner, _ = scored_candidates[j]
                    
                    # Verify partner hasn't reached their limit in the meantime
                    partner_max = self._get_max_partners(partner, "non_exclusive")
                    if partner.id in partner_counts and partner_counts[partner.id] >= partner_max:
                        continue
                    
                    # Create the relationship
                    self._create_relationship(person, partner, "non_exclusive")
                    
                    # Update partner counts for both people
                    partner_counts[person.id] = partner_counts.get(person.id, 0) + 1
                    partner_counts[partner.id] = partner_counts.get(partner.id, 0) + 1
                    
                    # Check if either person has reached their maximum
                    if partner_counts[person.id] >= max_partners:
                        break
    
    def _create_cheating_relationships(
        self, 
        potential_cheaters: List[Person], 
        non_exclusive_seekers: List[Person],
        household_partners: Dict[int, Set[int]]
    ) -> None:
        """
        Create non-consensual relationships for people who cheat on exclusive partners.
        Uses Person helper methods for relationship management.
        
        Parameters
        ----------
        potential_cheaters:
            List of people who might cheat
        non_exclusive_seekers:
            List of people open to non-exclusive relationships
        household_partners:
            Dictionary mapping person IDs to sets of partner IDs from household distributor
        """
        # Track current partner counts for all people to enforce limits
        partner_counts = {}
        
        # Initialise all potential cheaters
        for person in potential_cheaters:
            partner_counts[person.id] = len(person.sexual_partners.get("non_exclusive", set()))
                    
        # Initialise all non-exclusive seekers
        for person in non_exclusive_seekers:
            partner_counts[person.id] = len(person.sexual_partners.get("non_exclusive", set()))
        
        for cheater in potential_cheaters:
            # Skip if over limit already
            if partner_counts.get(cheater.id, 0) >= self._get_max_partners(cheater, "non_consensual"):
                continue
                
            # Decide if this potential cheater actually cheats
            cheating_prob = self._calculate_cheating_probability(cheater)
            
            if np.random.random() < cheating_prob:
                # Get maximum partners for this cheater
                max_partners = self._get_max_partners(cheater, "non_consensual")
                
                # Skip if max_partners is 0 or if cheater already has enough non-exclusive partners
                current_partners = partner_counts.get(cheater.id, 0)
                if max_partners <= 0 or current_partners >= max_partners:
                    continue
                
                # Determine remaining partners allowed
                remaining_slots = max_partners - current_partners
                
                # Usually just one relationship for cheating, with small chance of multiple affairs
                num_affairs = 1
                if remaining_slots > 1 and np.random.random() < 0.2:  # 20% chance of multiple affairs
                    num_affairs = min(2, remaining_slots)  # At most 2 affairs
                
                # Find compatible partners
                compatible_partners = self._find_compatible_partners(
                    cheater, 
                    non_exclusive_seekers, 
                    exclude_household=True,
                    household_partners=household_partners
                )
                
                if not compatible_partners:
                    continue
                
                # Filter by age-appropriateness
                age_appropriate = self._get_age_appropriate_partners(cheater, compatible_partners)
                
                if not age_appropriate:
                    age_appropriate = compatible_partners
                
                # Filter out candidates who have already reached their maximum partners
                valid_candidates = []
                for candidate in age_appropriate:
                    candidate_max = self._get_max_partners(candidate, "non_exclusive")
                    if partner_counts.get(candidate.id, 0) < candidate_max:
                        valid_candidates.append(candidate)
                
                if not valid_candidates:
                    continue
                
                # Create the affairs
                affairs_created = 0
                for _ in range(num_affairs):
                    if valid_candidates and affairs_created < remaining_slots:
                        # Select partner using compatibility scoring
                        partner = self._select_partner_by_score(cheater, valid_candidates, is_non_exclusive=True)
                        
                        if partner:
                            # Verify partner hasn't reached their limit in the meantime
                            partner_max = self._get_max_partners(partner, "non_exclusive")
                            if partner_counts.get(partner.id, 0) >= partner_max:
                                valid_candidates.remove(partner)
                                continue
                            
                            # Create the non-exclusive relationship
                            self._create_relationship(cheater, partner, "non_exclusive")
                            
                            # Mark relationship as non-consensual
                            self._mark_non_consensual_relationship(cheater)
                            
                            # Update partner counts
                            partner_counts[cheater.id] = partner_counts.get(cheater.id, 0) + 1
                            partner_counts[partner.id] = partner_counts.get(partner.id, 0) + 1
                            
                            # Remove this partner from future consideration
                            valid_candidates.remove(partner)
                            
                            # Increment affairs created
                            affairs_created += 1
        
    def _create_relationship(self, person1: Person, person2: Person, relationship_type: str) -> None:
        """
        Create a relationship between two people using Person helper methods.
        
        Parameters
        ----------
        person1:
            First person in the relationship
        person2:
            Second person in the relationship
        relationship_type:
            Type of relationship to create ("exclusive" or "non_exclusive")
        """
        # Use the Person helper method to add partners for both people
        person1.add_sexual_partner(person2.id, relationship_type)
        person2.add_sexual_partner(person1.id, relationship_type)
        
        # For exclusive relationships, the add_sexual_partner method already sets relationship_status
        # For non-exclusive relationships, we need to update the relationship status manually
        if relationship_type == "non_exclusive":
            if not person1.is_in_exclusive_relationship:  # Don't change status if already in exclusive relationship
                person1.relationship_status = {"type": "non_exclusive", "consensual": True}
            if not person2.is_in_exclusive_relationship:
                person2.relationship_status = {"type": "non_exclusive", "consensual": True}
    
    def _mark_non_consensual_relationship(self, person: Person) -> None:
        """
        Mark a person's relationship as non-consensual (cheating).
        
        Parameters
        ----------
        person:
            Person whose relationship status should be marked as non-consensual
        """
        if person.relationship_status.get("type") == "exclusive":
            person.relationship_status["consensual"] = False

    def _calculate_risk_profile(self, person: Person) -> Dict:
        """
        Calculate a multi-dimensional risk profile for a person based on their
        demographic characteristics and relationship status.
        
        Parameters
        ----------
        person:
            Person to calculate risk profile for
            
        Returns
        -------
        dict:
            Dictionary with various risk dimensions and testing frequency metrics
        """
        # Start with baseline values
        profile = {
            "behaviour_risk": 50,  # 0-100: risk from sexual behaviours
            "demographic_risk": 50,  # 0-100: risk from demographic factors
            "relationship_risk": 50,  # 0-100: risk from relationship patterns
            "testing_frequency": 5,  # 0-10 scale of testing likelihood
            "testing_consistency": 5,  # 0-10 scale of consistency in testing
        }
        
        # Load risk profile configuration - use safer defaultdict to avoid KeyErrors
        config = defaultdict(lambda: defaultdict(dict))
        if hasattr(self, 'risk_profile_config') and self.risk_profile_config:
            for category, values in self.risk_profile_config.items():
                for key, adjustment in values.items():
                    config[category][key] = adjustment
        
        # Age factors - apply from risk_profile_config if available
        age = person.age
        if age < 25 and '<25' in config.get('age_risk_factors', {}):
            factors = config['age_risk_factors']['<25']
            for key, value in factors.items():
                if key in profile:
                    profile[key] += value
        elif age < 35 and '25-35' in config.get('age_risk_factors', {}):
            factors = config['age_risk_factors']['25-35']
            for key, value in factors.items():
                if key in profile:
                    profile[key] += value
        elif age < 50 and '36-50' in config.get('age_risk_factors', {}):
            factors = config['age_risk_factors']['36-50']
            for key, value in factors.items():
                if key in profile:
                    profile[key] += value
        elif age < 65 and '51-65' in config.get('age_risk_factors', {}):
            factors = config['age_risk_factors']['51-65'] 
            for key, value in factors.items():
                if key in profile:
                    profile[key] += value
        elif '>65' in config.get('age_risk_factors', {}):
            factors = config['age_risk_factors']['>65']
            for key, value in factors.items():
                if key in profile:
                    profile[key] += value
        
        # Apply relationship factors
        if hasattr(person, "relationship_status"):
            rel_type = person.relationship_status.get("type", "no_partner")
            consensual = person.relationship_status.get("consensual", True)
            
            # Apply relationship risk factors from config if available
            relationship_key = None
            if rel_type == "exclusive" and consensual:
                relationship_key = "exclusive_consensual"
            elif rel_type == "exclusive" and not consensual:
                relationship_key = "exclusive_non_consensual"
            elif rel_type == "non_exclusive":
                relationship_key = "non_exclusive"
                
            if relationship_key and relationship_key in config.get('relationship_risk_factors', {}):
                factors = config['relationship_risk_factors'][relationship_key]
                for key, value in factors.items():
                    if key in profile:
                        profile[key] += value
        
        # Partner count factors
        partner_count = self._count_partners(person)
        if partner_count > 0:
            profile["behaviour_risk"] += min(partner_count * 8, 40)  # Cap at +40
            profile["testing_frequency"] += min(partner_count, 3)  # More partners, more testing
        
        # Gender/sex factors
        gender_key = person.sex
        if gender_key in config.get('gender_risk_factors', {}):
            factors = config['gender_risk_factors'][gender_key]
            for key, value in factors.items():
                if key in profile:
                    profile[key] += value
        
        # Sexual orientation factors
        if hasattr(person, "sexual_orientation"):
            orientation_key = None
            if person.sex == "m" and person.sexual_orientation == "homosexual":
                orientation_key = "m_homosexual"
            elif person.sexual_orientation == "bisexual":
                orientation_key = "bisexual"
                
            if orientation_key and orientation_key in config.get('orientation_risk_factors', {}):
                factors = config['orientation_risk_factors'][orientation_key]
                for key, value in factors.items():
                    if key in profile:
                        profile[key] += value
        
        # Educational factors (if available)
        if hasattr(person, "education") and isinstance(person.education, (int, float)):
            if person.education > 2:  # Higher education
                profile["testing_frequency"] += 1
                profile["testing_consistency"] += 2
        
        # Cap all values to their appropriate ranges
        for key in ["behaviour_risk", "demographic_risk", "relationship_risk"]:
            profile[key] = max(0, min(100, profile[key]))
        
        for key in ["testing_frequency", "testing_consistency"]:
            profile[key] = max(0, min(10, profile[key]))
            
        # Calculate overall risk score (weighted average)
        profile["overall_risk"] = (
            profile["behaviour_risk"] * 0.4 + 
            profile["demographic_risk"] * 0.3 + 
            profile["relationship_risk"] * 0.3
        )
        
        # Categorise testing frequency
        if profile["testing_frequency"] >= 8:
            profile["testing_category"] = "very_high"
        elif profile["testing_frequency"] >= 6:
            profile["testing_category"] = "high"
        elif profile["testing_frequency"] >= 4:
            profile["testing_category"] = "medium"
        elif profile["testing_frequency"] >= 2:
            profile["testing_category"] = "low"
        else:
            profile["testing_category"] = "very_low"
        
        return profile
    
    def _count_partners(self, person: Person) -> int:
        """
        Count the total number of sexual partners a person has.
        Uses the Person helper method.
        
        Parameters
        ----------
        person:
            Person to count partners for
            
        Returns
        -------
        int:
            Total number of partners across all relationship types
        """
        return person.count_partners()
    
    def _assign_risk_profiles(self, people: List[Person]) -> None:
        """
        Assign risk and testing profiles to all adults in the simulation.
        
        Parameters
        ----------
        people:
            List of people to assign risk profiles to
        """
        for person in people:
            # Skip children
            if person.age < 18:
                continue
                
            # Calculate and assign risk profile
            person.sexual_risk_profile = self._calculate_risk_profile(person)


    #============================================================= VISUALISATION TOOLS ===================================
        
    def _print_relationship_statistics(self, super_areas: List[SuperArea]) -> None:
        """
        Print statistics about the distribution of relationships.
        
        Parameters
        ----------
        super_areas:
            List of all super areas
        """
        # Initialise counters
        total_adults = 0
        no_partner = 0
        exclusive_consensual = 0
        exclusive_non_consensual = 0
        non_exclusive = 0
        
        # Count orientations
        orientations = defaultdict(int)
        
        # Age group stats
        age_groups = {
            "18-25": {"total": 0, "no_partner": 0, "exclusive": 0, "non_consensual": 0, "non_exclusive": 0},
            "26-35": {"total": 0, "no_partner": 0, "exclusive": 0, "non_consensual": 0, "non_exclusive": 0},
            "36-50": {"total": 0, "no_partner": 0, "exclusive": 0, "non_consensual": 0, "non_exclusive": 0},
            "51-64": {"total": 0, "no_partner": 0, "exclusive": 0, "non_consensual": 0, "non_exclusive": 0},
            "65+": {"total": 0, "no_partner": 0, "exclusive": 0, "non_consensual": 0, "non_exclusive": 0}
        }
        
        # Count shared primary activity relationships
        shared_activity_relationships = {
            "exclusive": 0,
            "non_exclusive": 0,
            "cheating": 0
        }
        total_relationships = {
            "exclusive": 0,
            "non_exclusive": 0,
            "cheating": 0
        }
        
        # Process all areas in each super area
        for super_area in super_areas:
            for area in super_area.areas:
                for person in area.people:
                    if person.age < 18:
                        continue
                        
                    total_adults += 1
                    
                    # Determine age group
                    age_group = None
                    if person.age < 26:
                        age_group = "18-25"
                    elif person.age < 36:
                        age_group = "26-35"
                    elif person.age < 51:
                        age_group = "36-50"
                    elif person.age < 65:
                        age_group = "51-64"
                    else:
                        age_group = "65+"
                    
                    age_groups[age_group]["total"] += 1
                    
                    # Count sexual orientations
                    if hasattr(person, "sexual_orientation"):
                        orientations[person.sexual_orientation] += 1

                    
                    
                    # Count relationship statuses
                    if not hasattr(person, "relationship_status"):
                        no_partner += 1
                        age_groups[age_group]["no_partner"] += 1
                    elif person.relationship_status["type"] == "no_partner":
                        no_partner += 1
                        age_groups[age_group]["no_partner"] += 1
                    elif person.relationship_status["type"] == "exclusive":
                        if person.relationship_status["consensual"]:
                            exclusive_consensual += 1
                            age_groups[age_group]["exclusive"] += 1
                            
                            # Check partner's activity for exclusive relationships
                            if hasattr(person, "sexual_partners") and "exclusive" in person.sexual_partners:
                                for partner_id in person.sexual_partners["exclusive"]:
                                    partner = self.person_dict.get(partner_id)
                                    if partner and partner.id > person.id:  # Count each relationship once
                                        total_relationships["exclusive"] += 1
                                        if self._have_same_primary_activity(person, partner):
                                            shared_activity_relationships["exclusive"] += 1
                        else:
                            exclusive_non_consensual += 1
                            age_groups[age_group]["non_consensual"] += 1
                            
                            # Check partner's activity for cheating relationships
                            if hasattr(person, "sexual_partners") and "non_exclusive" in person.sexual_partners:
                                for partner_id in person.sexual_partners["non_exclusive"]:
                                    partner = self.person_dict.get(partner_id)
                                    if partner and partner.id > person.id:
                                        total_relationships["cheating"] += 1
                                        if self._have_same_primary_activity(person, partner):
                                            shared_activity_relationships["cheating"] += 1
                    elif person.relationship_status["type"] == "non_exclusive":
                        non_exclusive += 1
                        age_groups[age_group]["non_exclusive"] += 1
                        
                        # Check partner's activity for non-exclusive relationships
                        if hasattr(person, "sexual_partners") and "non_exclusive" in person.sexual_partners:
                            for partner_id in person.sexual_partners["non_exclusive"]:
                                partner = self.person_dict.get(partner_id)
                                if partner and partner.id > person.id and partner.relationship_status["type"] == "non_exclusive":
                                    total_relationships["non_exclusive"] += 1
                                    if self._have_same_primary_activity(person, partner):
                                        shared_activity_relationships["non_exclusive"] += 1
        
        # Print statistics
        print("\n============================================================")
        print("               SEXUAL RELATIONSHIP STATISTICS")
        print("============================================================")
        print(f"Total adults: {total_adults}")
        print(f"No partner: {no_partner} ({no_partner/total_adults*100:.1f}%)")
        print(f"Exclusive consensual: {exclusive_consensual} ({exclusive_consensual/total_adults*100:.1f}%)")
        print(f"Exclusive non-consensual: {exclusive_non_consensual} ({exclusive_non_consensual/total_adults*100:.1f}%)")
        print(f"Non-exclusive: {non_exclusive} ({non_exclusive/total_adults*100:.1f}%)")
        
        print("\n----- Sexual Orientation Distribution -----")
        for orientation, count in orientations.items():
            print(f"{orientation}: {count} ({count/total_adults*100:.1f}%)")
        
        print("\n----- Age Group Relationship Statistics -----")
        for age_group, stats in age_groups.items():
            if stats["total"] > 0:
                print(f"\nAge Group: {age_group} (Total: {stats['total']})")
                print(f"  No partner: {stats['no_partner']} ({stats['no_partner']/stats['total']*100:.1f}%)")
                print(f"  Exclusive consensual: {stats['exclusive']} ({stats['exclusive']/stats['total']*100:.1f}%)")
                print(f"  Exclusive non-consensual: {stats['non_consensual']} ({stats['non_consensual']/stats['total']*100:.1f}%)")
                print(f"  Non-exclusive: {stats['non_exclusive']} ({stats['non_exclusive']/stats['total']*100:.1f}%)")
        
        print("\n----- Shared Primary Activity Statistics -----")
        for rel_type, count in shared_activity_relationships.items():
            total = total_relationships[rel_type]
            if total > 0:
                print(f"{rel_type} relationships with shared primary activity: {count} of {total} ({count/total*100:.1f}%)")
        
        print("============================================================")
        
        # Print count of potential cheaters
        print(f"Potential cheaters: {len(self.potential_cheaters)} people")
        print("============================================================")
        
        # Log sample persons
        self.log_sample_persons(super_areas, 10)  # Log 10 sample persons
        
    def log_sample_persons(self, super_areas: List[SuperArea], sample_size: int = 10) -> None:
        """
        Log detailed information about a sample of persons including their relationships.
        Ensures we sample a diverse set of relationship types, orientations, and living arrangements.
        
        Parameters
        ----------
        super_areas:
            List of all super areas
        sample_size:
            Number of persons to sample (default: 10)
        """
        print("\n============================================================")
        print("           SAMPLE PERSONS WITH RELATIONSHIP DETAILS")
        print("============================================================")
        
        # Group adults by various attributes for diverse sampling
        # By relationship type
        exclusive_consensual = []
        exclusive_non_consensual = []
        non_exclusive = []
        
        # By orientation
        heterosexual_people = []
        homosexual_people = []
        bisexual_people = []
        
        # By household arrangement
        shared_household_pairs = []  # Pairs of partners living in same household
        different_household_pairs = []  # Pairs of partners in different households
        
        # By shared activity
        shared_activity_pairs = []  # Pairs who share primary activity
        
        # By age group
        age_groups = {
            "18-25": [],
            "26-35": [],
            "36-50": [],
            "51-64": [],
            "65+": []
        }
        
        # Track all households with partners
        household_map = {}  # household_id -> list of people

        # Risk profile statistics
        behaviour_risk_avg = 0
        demographic_risk_avg = 0
        relationship_risk_avg = 0
        overall_risk_avg = 0
        total_with_profiles = 0
        
        for super_area in super_areas:
            for area in super_area.areas:
                for person in area.people:
                    if person.age < 18 or not hasattr(person, "relationship_status"):
                        continue
                        
                    rel_type = person.relationship_status.get("type", "unknown")
                    consensual = person.relationship_status.get("consensual", True)

                    if hasattr(person, "sexual_risk_profile"):                 
                        total_with_profiles += 1
                        sexual_risk_profile = person.sexual_risk_profile
                        behaviour_risk_avg += sexual_risk_profile["behaviour_risk"]
                        demographic_risk_avg += sexual_risk_profile["demographic_risk"]
                        relationship_risk_avg += sexual_risk_profile["relationship_risk"]
                        overall_risk_avg += sexual_risk_profile["overall_risk"]
                    
                    # Skip people with no partners
                    if rel_type == "no_partner":
                        continue
                        
                    # Make sure they have actual partners
                    if not hasattr(person, "sexual_partners") or not any(person.sexual_partners.values()):
                        continue
                    
                    # Add to age group
                    if person.age < 26:
                        age_groups["18-25"].append(person)
                    elif person.age < 36:
                        age_groups["26-35"].append(person)
                    elif person.age < 51:
                        age_groups["36-50"].append(person)
                    elif person.age < 65:
                        age_groups["51-64"].append(person)
                    else:
                        age_groups["65+"].append(person)
                    
                    # Get person's household ID
                    household_id = "N/A"
                    if (hasattr(person, "residence") and person.residence and 
                        hasattr(person.residence, "group")):
                        household_id = getattr(person.residence.group, "id", "N/A")
                        
                        # Track people by household
                        if household_id not in household_map:
                            household_map[household_id] = []
                        household_map[household_id].append(person)
                    
                    # Group by sexual orientation
                    orientation = getattr(person, "sexual_orientation", "unknown")
                    if orientation == "heterosexual":
                        heterosexual_people.append(person)
                    elif orientation == "homosexual":
                        homosexual_people.append(person)
                    elif orientation == "bisexual":
                        bisexual_people.append(person)
                        
                    # Add to appropriate relationship category
                    if rel_type == "exclusive":
                        if consensual:
                            exclusive_consensual.append(person)
                        else:
                            exclusive_non_consensual.append(person)
                    elif rel_type == "non_exclusive":
                        non_exclusive.append(person)
                        
                    # Find pairs living in same/different households
                    if hasattr(person, "sexual_partners"):
                        partner_types = ["exclusive", "non_exclusive"]
                        for partner_type in partner_types:
                            if partner_type in person.sexual_partners:
                                for partner_id in person.sexual_partners[partner_type]:
                                    partner = self.person_dict.get(partner_id)
                                    if partner and partner.id > person.id:  # Avoid duplicates
                                        # Check for shared household
                                        partner_household = "N/A"
                                        if (hasattr(partner, "residence") and partner.residence and 
                                            hasattr(partner.residence, "group")):
                                            partner_household = getattr(partner.residence.group, "id", "N/A")
                                        
                                        if household_id != "N/A" and household_id == partner_household:
                                            shared_household_pairs.append((person, partner))
                                        elif household_id != "N/A" and partner_household != "N/A" and household_id != partner_household:
                                            different_household_pairs.append((person, partner))
                                        
                                        # Check for shared activity
                                        if self._have_same_primary_activity(person, partner):
                                            shared_activity_pairs.append((person, partner))

        # Create a diverse sample
        sample_persons = []
        seen_households = set()  # To track household diversity
        
        # Print category counts
        print(f"\nCandidate pools:")
        print(f"Exclusive consensual: {len(exclusive_consensual)}")
        print(f"Exclusive non-consensual: {len(exclusive_non_consensual)}")
        print(f"Non-exclusive: {len(non_exclusive)}")
        print(f"Heterosexual people: {len(heterosexual_people)}")
        print(f"Homosexual people: {len(homosexual_people)}")
        print(f"Bisexual people: {len(bisexual_people)}")
        
        print(f"\nAge groups:")
        for age_group, people in age_groups.items():
            print(f"{age_group}: {len(people)}")
            
        print(f"\nHousehold and activity arrangements:")
        print(f"Same household pairs: {len(shared_household_pairs)}")
        print(f"Different household pairs: {len(different_household_pairs)}")
        print(f"Shared primary activity pairs: {len(shared_activity_pairs)}")
        
        if total_with_profiles > 0:
            print("\n----- Risk Profile Distribution -----")
            print(f"Average Behaviour Risk: {behaviour_risk_avg/total_with_profiles:.1f}/100")
            print(f"Average Demographic Risk: {demographic_risk_avg/total_with_profiles:.1f}/100")
            print(f"Average Relationship Risk: {relationship_risk_avg/total_with_profiles:.1f}/100")
            print(f"Average Overall Risk: {overall_risk_avg/total_with_profiles:.1f}/100")
        # Try to include one person from each relationship type
        categories = [
            (exclusive_consensual, "exclusive consensual"),
            (exclusive_non_consensual, "exclusive non-consensual"),
            (non_exclusive, "non-exclusive")
        ]
        
        for category, name in categories:
            if category:
                person = np.random.choice(category)
                if person not in sample_persons:
                    sample_persons.append(person)
                    print(f"Including sample from {name} relationships")
        
        # Try to include one person from each orientation
        orientation_categories = [
            (heterosexual_people, "heterosexual"),
            (homosexual_people, "homosexual"),
            (bisexual_people, "bisexual")
        ]
        
        for category, name in orientation_categories:
            if category and len(sample_persons) < sample_size:
                candidates = [p for p in category if p not in sample_persons]
                if candidates:
                    person = np.random.choice(candidates)
                    sample_persons.append(person)
                    print(f"Including sample with {name} orientation")
        
        # Try to include one person from each age group
        for age_group, people in age_groups.items():
            if people and len(sample_persons) < sample_size:
                candidates = [p for p in people if p not in sample_persons]
                if candidates:
                    person = np.random.choice(candidates)
                    sample_persons.append(person)
                    print(f"Including sample from age group {age_group}")
        
        # Try to include a person from a couple with shared primary activity
        if shared_activity_pairs and len(sample_persons) < sample_size:
            person1, person2 = np.random.choice(shared_activity_pairs)
            if person1 not in sample_persons:
                sample_persons.append(person1)
                print(f"Including person with shared primary activity relationship")
            if person2 not in sample_persons and len(sample_persons) < sample_size:
                sample_persons.append(person2)
                print(f"Including partner with shared primary activity relationship")
        
        # Try to include at least one couple from same household
        if shared_household_pairs and len(sample_persons) < sample_size:
            person1, person2 = np.random.choice(shared_household_pairs)
            if person1 not in sample_persons:
                sample_persons.append(person1)
                print(f"Including person from same-household couple")
            if person2 not in sample_persons and len(sample_persons) < sample_size:
                sample_persons.append(person2)
                print(f"Including partner from same-household couple")
        
        # Try to include at least one couple from different households
        if different_household_pairs and len(sample_persons) < sample_size:
            person1, person2 = np.random.choice(different_household_pairs)
            if person1 not in sample_persons:
                sample_persons.append(person1)
                print(f"Including person from different-household couple")
            if person2 not in sample_persons and len(sample_persons) < sample_size:
                sample_persons.append(person2)
                print(f"Including partner from different-household couple")
        
        # If we need more samples to reach sample_size, add randomly from all categories
        # but try to maximise household diversity
        all_adults = exclusive_consensual + exclusive_non_consensual + non_exclusive
        np.random.shuffle(all_adults)  # Shuffle to ensure randomness
        
        # Fill remaining slots with unique people from diverse households
        remaining_slots = sample_size - len(sample_persons)
        for person in all_adults:
            if person not in sample_persons and remaining_slots > 0:
                # Get household ID
                household_id = "N/A"
                if hasattr(person, "residence") and person.residence and hasattr(person.residence, "group"):
                    household_id = getattr(person.residence.group, "id", "N/A")
                
                # Prioritise people from new households if possible
                if household_id == "N/A" or household_id not in seen_households:
                    sample_persons.append(person)
                    if household_id != "N/A":
                        seen_households.add(household_id)
                    remaining_slots -= 1
            
            if remaining_slots == 0:
                break
        
        # If we still need more people, add anyone
        if remaining_slots > 0:
            for person in all_adults:
                if person not in sample_persons and remaining_slots > 0:
                    sample_persons.append(person)
                    remaining_slots -= 1
                if remaining_slots == 0:
                    break
                
        # Check if we have any samples
        if not sample_persons:
            print("No eligible adults with partners found for sampling.")
            return
            
        # Shuffle the final sample for randomness in presentation
        np.random.shuffle(sample_persons)
        
        # Log each sample person
        for i, person in enumerate(sample_persons, 1):
            # Get relationship status description
            relationship_type = person.relationship_status.get("type", "unknown")
            consensual = person.relationship_status.get("consensual", True)
            relationship_desc = relationship_type
            
            if relationship_type == "exclusive" and not consensual:
                relationship_desc = "exclusive (non-consensual)"
            
            # Get household ID if available
            household_id = "N/A"
            if hasattr(person, "residence") and person.residence and hasattr(person.residence, "group"):
                household_id = getattr(person.residence.group, "id", "N/A")
            
            # Get primary activity info if available
            primary_activity = "N/A"
            if (hasattr(person, 'subgroups') and person.subgroups and 
                hasattr(person.subgroups, 'primary_activity') and person.subgroups.primary_activity):
                primary_activity = str(person.subgroups.primary_activity)[:30]  # Truncate if too long
            
            # Print person details
            print(f"\nPERSON {i}: ID {person.id}")
            print(f"├─ Age: {person.age}, Gender: {person.sex}, "  
                  f"Orientation: {getattr(person, 'sexual_orientation', 'N/A')}")
            
            cheater_status = ""
            if relationship_desc == "exclusive (non-consensual)" or person.id in self.potential_cheaters:
                cheater_status = f", Potential Cheater: {'Yes' if person.id in self.potential_cheaters else 'No'}"
                
            print(f"├─ Relationship: {relationship_desc}{cheater_status}, "  
                  f"Household: {household_id}")
            print(f"├─ Primary Activity: {primary_activity}")
            
            # Print friends info if available
            if hasattr(person, 'friends') and person.friends:
                friend_count = len(person.friends) if isinstance(person.friends, (list, set)) else 1
                print(f"├─ Friends: {friend_count} friends")
            
            # Print super area info if available
            if hasattr(person, 'area') and person.area and hasattr(person.area, 'super_area'):
                print(f"├─ Super Area: {person.area.super_area.name}")

            # Print risk profile info if available
            if hasattr(person, "sexual_risk_profile"):
                sexual_risk_profile = person.sexual_risk_profile
                print(f"├─ Risk Profile:")
                print(f"│  ├─ Behaviour Risk: {sexual_risk_profile['behaviour_risk']}/100")
                print(f"│  ├─ Demographic Risk: {sexual_risk_profile['demographic_risk']}/100")
                print(f"│  ├─ Relationship Risk: {sexual_risk_profile['relationship_risk']}/100")
                print(f"│  ├─ Overall Risk: {sexual_risk_profile['overall_risk']:.1f}/100")
                print(f"│  ├─ Testing Frequency: {sexual_risk_profile['testing_frequency']}/10 ({sexual_risk_profile['testing_category']})")
                print(f"│  └─ Testing Consistency: {sexual_risk_profile['testing_consistency']}/10")
            
            # Print exclusive partners if any
            if hasattr(person, "sexual_partners") and "exclusive" in person.sexual_partners and person.sexual_partners["exclusive"]:
                print("├─ Exclusive Partners:")
                for partner_id in person.sexual_partners["exclusive"]:
                    partner = self.person_dict.get(partner_id)
                    if partner:
                        partner_household = getattr(partner.residence.group, "id", "N/A") if hasattr(partner, "residence") and partner.residence else "N/A"
                        partner_rel_desc = partner.relationship_status.get("type", "unknown")
                        if partner_rel_desc == "exclusive" and not partner.relationship_status.get("consensual", True):
                            partner_rel_desc = "exclusive (non-consensual)"
                            
                        # Check if from same super area
                        same_super_area = "No"
                        if (hasattr(person, 'area') and person.area and hasattr(person.area, 'super_area') and
                            hasattr(partner, 'area') and partner.area and hasattr(partner.area, 'super_area')):
                            same_super_area = "Yes" if person.area.super_area.name == partner.area.super_area.name else "No"
                        
                        # Check for common friends
                        common_friends = "No"
                        if hasattr(person, 'friends') and hasattr(partner, 'friends'):
                            if isinstance(person.friends, (list, set)) and isinstance(partner.friends, (list, set)):
                                if set(person.friends).intersection(set(partner.friends)):
                                    common_friends = "Yes"
                        
                        # Check for shared activity
                        shared_activity = "No"
                        if self._have_same_primary_activity(person, partner):
                            shared_activity = "Yes"
                            
                        partner_activity = "N/A"
                        if (hasattr(partner, 'subgroups') and partner.subgroups and 
                            hasattr(partner.subgroups, 'primary_activity') and partner.subgroups.primary_activity):
                            partner_activity = str(partner.subgroups.primary_activity)[:30]
                            
                        print(f"│  ├─ ID {partner.id}: Age {partner.age}, Gender: {partner.sex}, "  
                              f"Orientation: {getattr(partner, 'sexual_orientation', 'N/A')}")
                        print(f"│  ├─ Relationship: {partner_rel_desc}, Household: {partner_household}")
                        print(f"│  ├─ Primary Activity: {partner_activity}")
                        print(f"│  └─ Same Super Area: {same_super_area}, Common Friends: {common_friends}, Shared Activity: {shared_activity}")
                    else:
                        print(f"│  └─ ID {partner_id}: [Partner not found]")
            
            # Print non-exclusive partners if any
            if hasattr(person, "sexual_partners") and "non_exclusive" in person.sexual_partners and person.sexual_partners["non_exclusive"]:
                print("├─ Non-exclusive Partners:")
                for j, partner_id in enumerate(person.sexual_partners["non_exclusive"], 1):
                    partner = self.person_dict.get(partner_id)
                    if partner:
                        partner_household = getattr(partner.residence.group, "id", "N/A") if hasattr(partner, "residence") and partner.residence else "N/A"
                        partner_rel_desc = partner.relationship_status.get("type", "unknown")
                        if partner_rel_desc == "exclusive" and not partner.relationship_status.get("consensual", True):
                            partner_rel_desc = "exclusive (non-consensual)"
                            
                        # Check if from same super area
                        same_super_area = "No"
                        if (hasattr(person, 'area') and person.area and hasattr(person.area, 'super_area') and
                            hasattr(partner, 'area') and partner.area and hasattr(partner.area, 'super_area')):
                            same_super_area = "Yes" if person.area.super_area.name == partner.area.super_area.name else "No"
                        
                        # Check for common friends
                        common_friends = "No"
                        if hasattr(person, 'friends') and hasattr(partner, 'friends'):
                            if isinstance(person.friends, (list, set)) and isinstance(partner.friends, (list, set)):
                                if set(person.friends).intersection(set(partner.friends)):
                                    common_friends = "Yes"
                        
                        # Check for shared activity
                        shared_activity = "No"
                        if self._have_same_primary_activity(person, partner):
                            shared_activity = "Yes"
                            
                        partner_activity = "N/A"
                        if (hasattr(partner, 'subgroups') and partner.subgroups and 
                            hasattr(partner.subgroups, 'primary_activity') and partner.subgroups.primary_activity):
                            partner_activity = str(partner.subgroups.primary_activity)[:30]
                            
                        is_last = j == len(person.sexual_partners["non_exclusive"])
                        prefix = "└─" if is_last else "├─"
                            
                        print(f"│  {prefix} ID {partner.id}: Age {partner.age}, Gender: {partner.sex}, "  
                              f"Orientation: {getattr(partner, 'sexual_orientation', 'N/A')}")
                        print(f"{'    ' if is_last else '│  '}  ├─ Relationship: {partner_rel_desc}, Household: {partner_household}")
                        print(f"{'    ' if is_last else '│  '}  ├─ Primary Activity: {partner_activity}")
                        print(f"{'    ' if is_last else '│  '}  └─ Same Super Area: {same_super_area}, Common Friends: {common_friends}, Shared Activity: {shared_activity}")
                    else:
                        print(f"│  └─ ID {partner_id}: [Partner not found]")
        
        print("\n============================================================")
