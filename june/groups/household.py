from enum import IntEnum
from collections import defaultdict
import numpy as np
from random import random

from june.epidemiology.infection.disease_config import DiseaseConfig
from june.groups import Group, Supergroup
from june.groups.group.interactive import InteractiveGroup

from typing import List


class Household(Group):
    """
    The Household class represents a household and contains information about
    its residents.
    We assume four subgroups:
    0 - kids
    1 - young adults
    2 - adults
    3 - old adults
    """

    __slots__ = (
        "area",
        "type",
        "composition_type",
        "max_size",
        "residents",
        "quarantine_starting_date",
        "residences_to_visit",
        "being_visited",
        "household_to_care",
        "receiving_care"
    )

    # class SubgroupType(IntEnum):
    #     kids = 0
    #     young_adults = 1
    #     adults = 2
    #     old_adults = 3

    def __init__(self, type=None, area=None, max_size=np.inf, composition_type=None, registered_members_ids=None
    ):
        """
        Type should be on of ["family", "student", "young_adults", "old", "other", "nokids", "ya_parents", "communal"].
        Relatives is a list of people that are related to the family living in the household
        """

        super().__init__()        
        self.area = area
        self.type = type
        self.quarantine_starting_date = -99
        self.max_size = max_size
        self.residents = ()
        self.residences_to_visit = defaultdict(tuple)
        self.household_to_care = None
        self.being_visited = False  # this is True when people from other households have been added to the group
        self.receiving_care = False
        self.composition_type = composition_type
        self.registered_members_ids = registered_members_ids if registered_members_ids is not None else {}

    def _get_leisure_subgroup_for_person(self, person):
        if person.age < 18:
            subgroup = self.SubgroupType.kids
        elif person.age <= 25:
            subgroup = self.SubgroupType.young_adults
        elif person.age < 65:
            subgroup = self.SubgroupType.adults
        else:
            subgroup = self.SubgroupType.old_adults
        return subgroup
    
    def add_to_registered_members(self, person_id, subgroup_type=0):
        """
        Add a person to the registered members list for a specific subgroup.
        
        Parameters
        ----------
        person_id : int
            The ID of the person to add
        subgroup_type : int, optional
            The subgroup to add the person to (default: 0)
        """
        # Create the subgroup if it doesn't exist
        if subgroup_type not in self.registered_members_ids:
            self.registered_members_ids[subgroup_type] = []
            
        # Add the person if not already in the list
        if person_id not in self.registered_members_ids[subgroup_type]:
            self.registered_members_ids[subgroup_type].append(person_id)

    def add(self, person, subgroup_type=None, activity="residence"):
        if subgroup_type is None:
            subgroup_type = self.get_leisure_subgroup_type(person)

        if activity == "leisure":
            subgroup_type = self.get_leisure_subgroup_type(person)
            person.subgroups.leisure = self[subgroup_type]
            self[subgroup_type].append(person)
            self.being_visited = True
        elif activity == "residence":
            self[subgroup_type].append(person)
            self.residents = tuple((*self.residents, person))
            person.subgroups.residence = self[subgroup_type]
        else:
            raise NotImplementedError(f"Activity {activity} not supported in household")

    def get_leisure_subgroup_type(cls, person):
        """
        A person wants to come and visit this household. We need to assign the person
        to the relevant age subgroup, and make sure the residents welcome him and
        don't go do any other leisure activities.
        """
        if person.age < 18:
            return cls.SubgroupType.kids
        elif person.age <= 25:
            return cls.SubgroupType.young_adults
        elif person.age < 65:
            return cls.SubgroupType.adults
        else:
            return cls.SubgroupType.old_adults

    def make_household_residents_stay_home(self, to_send_abroad=None):
        """
        Forces the residents to stay home if they are away doing leisure.
        This is used to welcome visitors.
        """
        for mate in self.residents:
            if mate.busy:
                if (
                    mate.leisure is not None
                ):  # this person has already been assigned somewhere
                    if not mate.leisure.external:
                        if mate not in mate.leisure.people:
                            # person active somewhere else, let's not disturb them
                            continue
                        mate.leisure.remove(mate)
                    else:
                        ret = to_send_abroad.delete_person(mate, mate.leisure)
                        if ret:
                            # person active somewhere else, let's not disturb them
                            continue
                    mate.subgroups.leisure = mate.residence
                    mate.residence.append(mate)
            else:
                mate.subgroups.leisure = (
                    mate.residence  # person will be added later in the simulator.
                )

    # @property
    # def kids(self):
    #     return self.subgroups[self.SubgroupType.kids]

    # @property
    # def young_adults(self):
    #     return self.subgroups[self.SubgroupType.young_adults]

    # @property
    # def adults(self):
    #     return self.subgroups[self.SubgroupType.adults]

    # @property
    # def old_adults(self):
    #     return self.subgroups[self.SubgroupType.old_adults]

    @property
    def coordinates(self):
        return self.area.coordinates

    @property
    def n_residents(self):
        return len(self.residents)

    def quarantine(self, time, quarantine_days, household_compliance):
        if self.type == "communal":
            return False
        if self.quarantine_starting_date:
            if (
                self.quarantine_starting_date
                < time
                < self.quarantine_starting_date + quarantine_days
            ):
                return random() < household_compliance
        return False

    @property
    def super_area(self):
        try:
            return self.area.super_area
        except AttributeError:
            return None

    def clear(self):
        super().clear()
        self.being_visited = False
        self.receiving_care = False

    def get_interactive_group(self, people_from_abroad=None):
        return InteractiveHousehold(self, people_from_abroad=people_from_abroad)

    def get_leisure_subgroup(self, person, subgroup_type, to_send_abroad):
        self.being_visited = True
        self.make_household_residents_stay_home(to_send_abroad=to_send_abroad)
        return self[self._get_leisure_subgroup_for_person(person=person)]
    
    def get_all_registered_members_ids(self):
    
        all_member_ids = [member_id for subgroup_members in self.registered_members_ids.values() 
                    for member_id in subgroup_members]
        
        return all_member_ids


class Households(Supergroup):
    """
    Contains all households for the given area, and information about them.
    """

    venue_class = Household

    def __init__(self, households: List[venue_class]):
        super().__init__(members=households)


class InteractiveHousehold(InteractiveGroup):
    def has_isolating_residents(self, current_time):
        """
        Check if any household residents are currently in self-isolation.
        
        Parameters
        ----------
        current_time : float
            Current simulation time in days from start
            
        Returns
        -------
        bool
            True if any resident is currently in isolation, False otherwise
        """
        if current_time is None:
            return False
            
        for person in self.group.residents:
            if (hasattr(person, 'test_and_trace') and 
                person.test_and_trace is not None and
                person.test_and_trace.isolation_start_time is not None and
                person.test_and_trace.isolation_end_time is not None):
                
                # Check if we're currently within the isolation period
                if (person.test_and_trace.isolation_start_time <= current_time <= 
                    person.test_and_trace.isolation_end_time):
                    return True
        return False
    
    def get_processed_beta(self, betas, beta_reductions, current_time=None):
        """
        Enhanced version that applies isolation precautions if residents are isolating.
        
        In the case of households, we need to apply the beta reduction of household visits
        if the household has a visit, otherwise we apply the beta reduction for a normal
        household. Additionally, if any residents are in isolation, we apply extra
        precautionary reductions to model social distancing within the household.
        
        Parameters
        ----------
        betas : dict
            Base transmission intensities for different venue types
        beta_reductions : dict
            Policy-based beta reductions
        current_time : float, optional
            Current simulation time in days from start
            
        Returns
        -------
        float
            Final processed beta value for this household
        """
        # Determine base beta and spec based on household state
        if self.group.receiving_care:
            # important than this goes first than being visited
            beta = betas["care_visits"]
            spec = "care_visits"
        elif self.group.being_visited:
            beta = betas["household_visits"]
            spec = "household_visits"
        else:
            beta = betas["household"]
            spec = "household"
        
        # Get standard policy reduction
        beta_reduction = beta_reductions.get(spec, 1.0)
        
        # Apply isolation precautions if anyone is isolating
        if current_time is not None and self.has_isolating_residents(current_time):
            # Additional reductions for isolation precautions
            isolation_precautions = {
                "household": 0.7,        # 30% reduction in household transmission
                "household_visits": 0.1, # 90% reduction in visits (discouraged)
                "care_visits": 0.6       # 40% reduction in care visits (extra PPE/precautions)
            }
            isolation_reduction = isolation_precautions.get(spec, 1.0)
            beta_reduction *= isolation_reduction
                    
        # Apply regional compliance and return final beta
        regional_compliance = self.super_area.region.regional_compliance
        final_beta = beta * (1 + regional_compliance * (beta_reduction - 1))
        
        return final_beta