from dataclasses import field, dataclass
from itertools import count
from random import choice
from recordclass import dataobject
from june.epidemiology.test_and_trace import TestAndTrace
from june.mpi_wrapper import MPI, mpi_rank, mpi_comm, mpi_size, mpi_available
from datetime import datetime

from june.epidemiology.infection import Infection, Immunity

from typing import TYPE_CHECKING, Any, ClassVar, Dict, Optional, Set, List, Tuple

if TYPE_CHECKING:
    from june.geography.geography import Area
    from june.geography.geography import SuperArea
    from june.groups.travel.mode_of_transport import ModeOfTransport
    from june.epidemiology.vaccines.vaccines import VaccineTrajectory


class Activities(dataobject):
    residence: None
    primary_activity: None
    medical_facility: None
    commute: None
    rail_travel: None
    leisure: None
    international_travel: None

    def iter(self):
        return [getattr(self, activity) for activity in self.__fields__]


person_ids = count()

@dataclass(slots=True)
class Person:
    _id_generator: ClassVar[count] = count()
    _persons: ClassVar[Dict[int, "Person"]] = {}

    id: int = field(default_factory=lambda: next(Person._id_generator))
    sex: str = "f"
    age: int = 27
    ethnicity: str = None
    area: "Area" = None
    work_super_area: "SuperArea" = None
    sector: str = None
    sub_sector: str = None
    lockdown_status: str = None
    vaccine_trajectory: "VaccineTrajectory" = None
    vaccinated: int = None
    vaccine_type: str = None
    comorbidity: str = None
    mode_of_transport: "ModeOfTransport" = None
    hobbies: list = field(default_factory=list)
    _friends: Dict[int, int] = field(default_factory=dict)  # {friend_id: home_rank}
    busy: bool = False
    subgroups: Activities = None
    infection: Infection = None
    immunity: Immunity = None
    test_and_trace: TestAndTrace = None
    dead: bool = False
    _current_rank: int = field(default=-1)  # Store current rank
    _home_rank: int = field(default=-1)  # Store home rank
    ## mpox
    relationship_status: Dict[str, Any] = field(default_factory=lambda: {"type": "no_partner", "consensual": True})
    sexual_partners: Dict[str, Set[int]] = field(default_factory=lambda: {"exclusive": set(), "non_exclusive": set()})
    sexual_orientation: str = None
    sexual_risk_profile: Dict = field(default_factory=dict)
    _activity_overrides: Dict[str, datetime] = field(default_factory=dict)  # activity -> end_date
    _original_activities: Dict[str, Any] = field(default_factory=dict)  # Store original activities
    _travel_status: Dict[str, Any] = field(default_factory=lambda: {
        "is_traveling": False,
        "current_location": None,  # Either Area or ForeignDestination
        "accumulated_exposure": 0.0,  # Tracks exposure during travel
        "exposure_history": [],  # List of (location, exposure) tuples
        "travel_start": None,  # When travel began
        "destinations_visited": []  # Track travel history
    })
    # Temporary attributes for friend invitation system
    _accepted_invitation_this_round: bool = field(default=False)
    _pending_friend_assignment: Optional[Any] = field(default=None)

    def __post_init__(self):
        """Register the new person and initialize MPI-related attributes"""
        Person._persons[self.id] = self
        # Always initialize current rank to the MPI rank where the person is created
        self._home_rank = 0 if not mpi_available else mpi_rank  # Default to 0 in non-MPI mode
        self._current_rank = 0 if not mpi_available else mpi_rank
        # Initialize an empty friends dictionary if not already set
        if not hasattr(self, '_friends'):
            self._friends = {}

    @property
    def friends(self) -> Dict[int, int]:
        """Get the dictionary of friend IDs and home ranks"""
        return self._friends
    
    @friends.setter
    def friends(self, friend_dict: Dict[int, int]):
        """Set friend IDs and home ranks"""
        self._friends = dict(friend_dict)

    @classmethod
    def find_by_id(cls, person_id: int) -> "Person":
        """Retrieve a Person instance by their ID."""
        person_id = int(person_id)  # Convert to standard Python int
        person = cls._persons.get(person_id)
        return person
    
    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        # Fast path: if other is not a Person, return False immediately
        # without doing isinstance check
        try:
            return self.id == other.id
        except AttributeError:
            return False
        
    @classmethod
    def from_attributes(
        cls,
        sex="f",
        age=27,
        susceptibility_dict: dict = None,
        ethnicity=None,
        id=None,
        comorbidity=None,
    ):
        # Use _id_generator if no id is provided
        if id is None:
            id = next(cls._id_generator)
        
        # Create a new person instance
        person = cls(
            id=id,
            sex=sex,
            age=age,
            ethnicity=ethnicity,
            immunity=Immunity(susceptibility_dict=susceptibility_dict),
            comorbidity=comorbidity,
            subgroups=Activities(None, None, None, None, None, None, None),
        )

        # Ensure the new person is registered in the dictionary
        cls._persons[id] = person

        # Explicitly initialize the friends attribute
        person.friends = {}

        return person
    

    @property
    def infected(self):
        return self.infection is not None

    @property
    def residence(self):
        return self.subgroups.residence

    @property
    def primary_activity(self):
        return self.subgroups.primary_activity

    @property
    def medical_facility(self):
        return self.subgroups.medical_facility

    @property
    def commute(self):
        return self.subgroups.commute

    @property
    def rail_travel(self):
        return self.subgroups.rail_travel

    @property
    def leisure(self):
        return self.subgroups.leisure

    @property
    def international_travel(self):
        return self.subgroups.international_travel
    
    @property
    def hospitalised(self):
        try:
            return all(
                [
                    self.medical_facility.group.spec == "hospital",
                    self.medical_facility.subgroup_type
                    == self.medical_facility.group.SubgroupType.patients,
                ]
            )
        except AttributeError:
            return False

    @property
    def intensive_care(self):
        try:
            return all(
                [
                    self.medical_facility.group.spec == "hospital",
                    self.medical_facility.subgroup_type
                    == self.medical_facility.group.SubgroupType.icu_patients,
                ]
            )
        except AttributeError:
            return False

    @property
    def housemates(self):
        if self.residence.group.spec == "care_home":
            return []
        return self.residence.group.residents

    def find_guardian(self):
        possible_guardians = [person for person in self.housemates if person.age >= 18]
        if not possible_guardians:
            return None
        guardian = choice(possible_guardians)
        if (
            guardian.infection is not None and guardian.infection.should_be_in_hospital
        ) or guardian.dead:
            return None
        else:
            return guardian

    @property
    def symptoms(self):
        if self.infection is None:
            return None
        else:
            return self.infection.symptoms

    @property
    def super_area(self):
        try:
            return self.area.super_area
        except Exception:
            return None

    @property
    def region(self):
        try:
            return self.super_area.region
        except Exception:
            return None

    @property
    def home_city(self):
        return self.area.super_area.city

    @property
    def work_city(self):
        if self.work_super_area is None:
            return None
        return self.work_super_area.city

    @property
    def available(self):
        if (not self.dead) and (self.medical_facility is None) and (not self.busy):
            return True
        return False

    @property
    def socioeconomic_index(self):
        try:
            return self.area.socioeconomic_index
        except Exception:
            return

    def add_sexual_partner(self, partner_id: int, relationship_type: str = "exclusive"):
        """
        Add a sexual partner with specified relationship type.
        
        Parameters
        ----------
        partner_id: int
            ID of the partner to add
        relationship_type: str
            Type of relationship ("exclusive" or "non_exclusive")
        """
        if not hasattr(self, "sexual_partners") or not isinstance(self.sexual_partners, dict):
            self.sexual_partners = {"exclusive": set(), "non_exclusive": set()}
            
        if relationship_type not in self.sexual_partners:
            self.sexual_partners[relationship_type] = set()
            
        self.sexual_partners[relationship_type].add(partner_id)
        
        # Update relationship status if adding exclusive partner
        if relationship_type == "exclusive":
            self.relationship_status = {"type": "exclusive", "consensual": True}
    
    def remove_sexual_partner(self, partner_id: int, relationship_type: str = None):
        """
        Remove a sexual partner from specified relationship type or all types.
        
        Parameters
        ----------
        partner_id: int
            ID of the partner to remove
        relationship_type: str, optional
            Type of relationship to remove from. If None, remove from all.
        """
        if not hasattr(self, "sexual_partners") or not isinstance(self.sexual_partners, dict):
            return
            
        if relationship_type is None:
            # Remove from all relationship types
            for rel_type in self.sexual_partners:
                self.sexual_partners[rel_type].discard(partner_id)
        elif relationship_type in self.sexual_partners:
            # Remove from specified relationship type
            self.sexual_partners[relationship_type].discard(partner_id)
        
        # Update relationship status if no partners left
        no_partners_left = True
        for rel_type in self.sexual_partners:
            if self.sexual_partners[rel_type]:
                no_partners_left = False
                break
                
        if no_partners_left:
            self.relationship_status = {"type": "no_partner", "consensual": True}
            
    @property
    def has_sexual_partners(self) -> bool:
        """Check if person has any sexual partners."""
        if not hasattr(self, "sexual_partners") or not isinstance(self.sexual_partners, dict):
            return False
            
        for rel_type in self.sexual_partners:
            if self.sexual_partners[rel_type]:
                return True
        return False
        
    @property
    def is_in_exclusive_relationship(self) -> bool:
        """Check if person is in an exclusive relationship."""
        if not hasattr(self, "relationship_status") or not isinstance(self.relationship_status, dict):
            return False
            
        return self.relationship_status.get("type") == "exclusive"
        
    @property 
    def is_in_non_exclusive_relationship(self) -> bool:
        """Check if person is in a non-exclusive relationship."""
        if not hasattr(self, "relationship_status") or not isinstance(self.relationship_status, dict):
            return False
            
        return self.relationship_status.get("type") == "non_exclusive"  
    
    @property
    def is_single(self) -> bool:
        """Check if person has no sexual partners."""
        return not self.has_sexual_partners

    @property
    def is_cheating(self) -> bool:
        """Check if person is cheating (exclusive but non-consensual)."""
        if not hasattr(self, "relationship_status") or not isinstance(self.relationship_status, dict):
            return False
            
        return (self.relationship_status.get("type") == "exclusive" and 
                not self.relationship_status.get("consensual", True))

    def set_relationship_status(self, rel_type: str, consensual: bool = True) -> None:
        """
        Set the relationship status type and whether it's consensual.
        
        Parameters
        ----------
        rel_type: str
            Relationship type ("exclusive", "non_exclusive", "no_partner")
        consensual: bool
            Whether the relationship is consensual
        """
        self.relationship_status = {"type": rel_type, "consensual": consensual}
        
        # If setting to no_partner, clear all partners
        if rel_type == "no_partner":
            self.sexual_partners = {"exclusive": set(), "non_exclusive": set()}
            
    def count_partners(self, relationship_type: str = None) -> int:
        """
        Count the number of partners of the specified type or all types.
        
        Parameters
        ----------
        relationship_type: str, optional
            If provided, count only partners of this type
            
        Returns
        -------
        int:
            Number of partners
        """
        if not hasattr(self, "sexual_partners") or not isinstance(self.sexual_partners, dict):
            return 0
            
        if relationship_type is not None:
            return len(self.sexual_partners.get(relationship_type, set()))
        else:
            return sum(len(partners) for partners in self.sexual_partners.values())
            
    def get_partners(self, relationship_type: str = None) -> Set[int]:
        """
        Get the set of partner IDs for the specified relationship type or all types.
        
        Parameters
        ----------
        relationship_type: str, optional
            If provided, get only partners of this type
            
        Returns
        -------
        Set[int]:
            Set of partner IDs
        """
        if not hasattr(self, "sexual_partners") or not isinstance(self.sexual_partners, dict):
            return set()
            
        if relationship_type is not None:
            return self.sexual_partners.get(relationship_type, set())
        else:
            # Combine partners of all types
            all_partners = set()
            for partners in self.sexual_partners.values():
                all_partners.update(partners)
            return all_partners

    def set_activity_override(
        self, 
        activity: str, 
        end_date: datetime,
        replacement_activity: Optional[Any] = None
    ) -> None:
        """
        Override a person's regular activity until specified end date.
        
        Parameters
        ----------
        activity : str
            Activity to override (e.g., "primary_activity")
        end_date : datetime
            When to end the override
        replacement_activity : Any, optional
            The temporary activity/subgroup to use
        """
        # Store original activity if not already stored
        if activity not in self._original_activities:
            self._original_activities[activity] = getattr(self.subgroups, activity)

        # Set the override end date
        self._activity_overrides[activity] = end_date

        # Set temporary activity if provided
        if replacement_activity is not None:
            setattr(self.subgroups, activity, replacement_activity)

    def clear_activity_override(self, activity: str) -> None:
        """
        Clear override and restore original activity
        
        Parameters
        ----------
        activity : str
            Activity to restore
        """
        if activity in self._activity_overrides:
            # Restore original activity if it exists
            if activity in self._original_activities:
                setattr(
                    self.subgroups, 
                    activity, 
                    self._original_activities[activity]
                )
                del self._original_activities[activity]
            
            # Remove override
            del self._activity_overrides[activity]

    def has_activity_override(self, activity: str, current_date: datetime) -> bool:
        """
        Check if activity is currently overridden
        
        Parameters
        ----------
        activity : str
            Activity to check
        current_date : datetime
            Current simulation date
            
        Returns
        -------
        bool:
            True if activity is overridden and override hasn't expired
        """
        if activity in self._activity_overrides:
            end_date = self._activity_overrides[activity]
            if current_date >= end_date:
                # Override expired - clear it
                self.clear_activity_override(activity)
                return False
            return True
        return False

    def get_current_activity(self, activity: str, current_date: datetime) -> Any:
        """
        Get the current activity, considering any active overrides
        
        Parameters
        ----------
        activity : str
            Activity to get
        current_date : datetime
            Current simulation date
            
        Returns
        -------
        Any:
            Current activity/subgroup
        """
        if self.has_activity_override(activity, current_date):
            return getattr(self.subgroups, activity)
        return self._original_activities.get(activity, getattr(self.subgroups, activity))

    @property
    def is_traveling(self) -> bool:
        """Check if person is currently traveling"""
        return self._travel_status["is_traveling"]
    
    @property
    def current_location(self) -> Any:
        """Get person's current location (Area or ForeignDestination)"""
        return self._travel_status["current_location"]

    @property
    def accumulated_exposure(self) -> float:
        """Get total exposure accumulated during travel"""
        return self._travel_status["accumulated_exposure"]

    def start_travel(self, destination: Any, date: datetime) -> None:
        """
        Mark person as starting travel to a destination
        
        Parameters
        ----------
        destination : Area or ForeignDestination
            Where the person is traveling to
        date : datetime
            When travel begins
        """
        self._travel_status.update({
            "is_traveling": True,
            "current_location": destination,
            "travel_start": date,
            "accumulated_exposure": 0.0
        })
        self._travel_status["destinations_visited"].append(destination)

    def end_travel(self) -> None:
        """End travel and reset status"""
        # Save exposure record before clearing
        if self._travel_status["accumulated_exposure"] > 0:
            self._travel_status["exposure_history"].append(
                (self._travel_status["current_location"], 
                 self._travel_status["accumulated_exposure"])
            )
        
        # Reset travel status
        self._travel_status.update({
            "is_traveling": False,
            "current_location": self.area,  # Reset to home area
            "accumulated_exposure": 0.0,
            "travel_start": None
        })

    def add_travel_exposure(self, exposure: float, location: Any = None) -> None:
        """
        Add to person's accumulated exposure during travel
        
        Parameters
        ----------
        exposure : float
            Amount of exposure to add
        location : Any, optional
            Location where exposure occurred (if different from current)
        """
        if not self.is_traveling:
            return
            
        self._travel_status["accumulated_exposure"] += exposure
        
        # Update location if provided
        if location:
            # Save exposure record for previous location
            if self._travel_status["current_location"]:
                self._travel_status["exposure_history"].append(
                    (self._travel_status["current_location"], 
                     self._travel_status["accumulated_exposure"])
                )
            # Reset exposure counter for new location    
            self._travel_status["current_location"] = location
            self._travel_status["accumulated_exposure"] = exposure

    def get_travel_history(self) -> List[Tuple[Any, float]]:
        """
        Get list of visited locations and accumulated exposure at each
        
        Returns
        -------
        List[Tuple[Any, float]]:
            List of (location, exposure) pairs
        """
        history = self._travel_status["exposure_history"].copy()
        # Add current location if traveling
        if self.is_traveling and self.accumulated_exposure > 0:
            history.append(
                (self.current_location, self.accumulated_exposure)
            )
        return history
    
    def get_leisure_companions(self, days_back=None):
        """
        Get leisure companions for this person.
        
        Note: The days_back parameter is deprecated. Contact age filtering 
        is now handled centrally by ContactManager.clean_old_contacts().
        
        Parameters
        ----------
        days_back : int, optional
            Deprecated parameter, ignored. Retained for backward compatibility.
            
        Returns
        -------
        dict
            Dictionary mapping companion_id to companion info
        """
        # This requires access to the simulation's contact manager
        # In a real implementation, you might want to store a reference to the simulation
        # or contact manager in the person object, or access it through a global context
        from june.global_context import GlobalContext
        
        simulator = GlobalContext.get_simulator()
        if simulator and simulator.contact_manager:
            return simulator.contact_manager.get_recent_leisure_companions(self.id)
        return {}
    
    def get_all_leisure_companions(self):
        """
        Get all leisure companions for this person.
        
        Returns
        -------
        dict
            Dictionary mapping companion_id to companion info
        """
        from june.global_context import GlobalContext
        
        simulator = GlobalContext.get_simulator()
        if simulator and simulator.contact_manager:
            return simulator.contact_manager.get_leisure_companions(self.id)
        return {}

