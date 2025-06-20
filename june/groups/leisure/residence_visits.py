import yaml
from random import shuffle, randint
import numpy as np
import pandas as pd

from june.groups.leisure import SocialVenueDistributor
from june.paths import configs_path
from june.utils import random_choice_numba
from june.mpi_wrapper import mpi_rank, mpi_available

default_config_filename = configs_path / "defaults/groups/leisure/visits.yaml"

default_daytypes = {
    "weekday": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "weekend": ["Saturday", "Sunday"],
}


class ResidenceVisitsDistributor(SocialVenueDistributor):
    """
    This is a social distributor specific to model visits between residences,
    ie, visits between households or to care homes. The meaning of the parameters
    is the same as for the SVD. Residence visits are not decied on neighbours or distances
    so we ignore some parameters.
    """

    def __init__(
        self,
        residence_type_probabilities,
        times_per_week,
        hours_per_day,
        daytypes=default_daytypes,
        drags_household_probability=0,
        invites_friends_probability=0
    ):
        # it is necessary to make them arrays for performance
        self.residence_type_probabilities = residence_type_probabilities
        self.policy_reductions = {}
        super().__init__(
            social_venues=None,
            times_per_week=times_per_week,
            daytypes=daytypes,
            hours_per_day=hours_per_day,
            drags_household_probability=drags_household_probability,
            invites_friends_probability=invites_friends_probability,
            neighbours_to_consider=None,
            maximum_distance=None,
            leisure_subgroup_type=None,
        )

    @classmethod
    def from_config(cls, daytypes, config_filename: str = default_config_filename):
        # Load the configuration file
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        # Display configuration data for visualization
        #print("\n===== Loaded Configuration Settings =====")
        config_df = pd.DataFrame([config])  # Convert config to DataFrame for readability
        #print(config_df)

        # Display daytypes information based on its structure
        #print("\n===== Daytypes Information =====")
        #try:
            # Convert daytypes to DataFrame appropriately
            #daytypes_df = pd.DataFrame(daytypes)
            #print(daytypes_df)
        #except ValueError:
            #print("Unable to display daytypes as a DataFrame directly.")
            #for key, value in daytypes.items():
                #print(f"{key}: {value}")

        # Create and return the instance
        return cls(daytypes=daytypes, **config)
    
    def _get_visited_residents(self, person):
        """
        Get the residents of the place a person is visiting (household or care home)
        
        Parameters
        ----------
        person : Person
            The person who is visiting
            
        Returns
        -------
        list
            List of residents at the visited location
        """
        # Get the leisure group (residence being visited)
        visited_group = person.leisure.group if person.leisure and hasattr(person.leisure, 'group') else None
        
        if not visited_group:
            return []
            
        # Get the residents of the visited location
        if hasattr(visited_group, 'residents'):
            return [resident for resident in visited_group.residents if resident != person]
        else:
            return []

    def coordinate_invitations(self, person, activity, to_send_abroad=None):
        """
        Coordinate invitations for residence visits - simplifies the base class version
        since residences are always local
        
        Returns:
            list: List of all people who were invited
        """
        invited_people = []  # List to track all invited people
        
        # Get invitation priority from social network
        priority = self.social_network.decide_invitation(person, activity)

        # Define priority actions
        actions = {
            "household": self.person_drags_household,
            "friends": self.person_invites_friends,
        }

        # Try primary priority
        if actions[priority]():
            if priority == "household":
                household_invitees = self._coordinate_household_invitations(person, to_send_abroad)
                invited_people.extend(household_invitees or [])
            else:
                friend_invitees = self._coordinate_friend_invitations(person, to_send_abroad)
                invited_people.extend(friend_invitees or [])
        else:
            # Try fallback priority
            other_priority = "friends" if priority == "household" else "household"
            if actions[other_priority]():
                if other_priority == "household":
                    household_invitees = self._coordinate_household_invitations(person, to_send_abroad)
                    invited_people.extend(household_invitees or [])
                else:
                    friend_invitees = self._coordinate_friend_invitations(person, to_send_abroad)
                    invited_people.extend(friend_invitees or [])
                    
        # Get residents of the location we're visiting to add to contacts
        visit_residents = self._get_visited_residents(person)
        
        # Add them to the list of invited people for contact tracking
        invited_people.extend(visit_residents)
                    
        return invited_people
    
    def _coordinate_household_invitations(self, person, to_send_abroad):
        """
        Handle household invitations for residence visits
        
        Returns:
            list: List of household members who were invited
        """
        if person.residence.group.spec in ["care_home", "communal", "other", "student"]:
            return []
            
        people_to_bring = [
            mate for mate in person.residence.group.residents 
            if mate != person
        ]
        self.bring_people_with_person(person, people_to_bring, to_send_abroad)
        return people_to_bring

    def _coordinate_friend_invitations(self, person, to_send_abroad):
        """
        Handle friend invitations for residence visits
        
        Returns:
            list: List of friends who were invited locally
        """
        if person.residence.group.spec == "care_home":
            return []

        friend_candidates = self.invite_friends_with_hobbies(person)
        invited_friends = []
        
        # Get the current rank - default to 0 in non-MPI mode
        current_rank = 0 if not mpi_available else mpi_rank
        
        # For residence visits, we only handle local friends
        local_friends = [
            friend for friend in friend_candidates 
            if friend.get_friend_rank(friend.id) == current_rank
        ]
        
        if local_friends:
            self.bring_people_with_person(person, local_friends, to_send_abroad)
            invited_friends.extend(local_friends)
            
        return invited_friends

    def _send_friend_invitation(self, person, friend, friend_rank):
        """
        For residence visits, we don't send remote invitations.
        Friends must be local to visit residences.
        """
        pass  # No remote invitations for residence visits

    def link_households_to_households(self, super_areas):
        """
        Links people between households. Strategy: We pair each household with 0, 1,
        or 2 other households (with equal prob.). The household of the former then
        has a probability of visiting the household of the later
        at every time step.

        Parameters
        ----------
        super_areas
            list of super areas
        """

        # Collect data for visualization
        linked_households_data = []

        for super_area in super_areas:
            households_in_super_area = [
                household for area in super_area.areas for household in area.households
            ]
            for household in households_in_super_area:
                if household.n_residents == 0:
                    continue
                households_to_link_n = randint(2, 4)
                households_to_visit = []
                n_linked = 0
                while n_linked < households_to_link_n:
                    house_idx = randint(0, len(households_in_super_area) - 1)
                    house = households_in_super_area[house_idx]
                    if house.id == household.id or not house.residents:
                        continue
                    households_to_visit.append(house)
                    n_linked += 1
                if households_to_visit:
                    household.residences_to_visit["household"] = tuple(
                        households_to_visit
                    )

                    # Collect data for this household
                    linked_households_data.append({
                        "Household ID": household.id,
                        "Super Area": super_area.name,
                        "Household Type": household.type,
                        "Number of Residents": household.n_residents,
                        "Linked Household IDs": [linked_house.id for linked_house in households_to_visit]
                    })

        # Display the collected data in a DataFrame for a sample
        df_linked_households = pd.DataFrame(linked_households_data)
        print("\n===== Sample of Linked Households =====")
        print(df_linked_households.sample(n=10))  # Show a random sample of 10 linked households

    def link_households_to_care_homes(self, super_areas):
        """
        Links households and care homes in the giving super areas. For each care home,
        we find a random house in the super area and link it to it.
        The house needs to be occupied by a family, or a couple.

        Parameters
        ----------
        super_areas
            list of super areas
        """
        # Collect data for visualization
        care_home_link_data = []
        for super_area in super_areas:
            households_super_area = []
            for area in super_area.areas:
                households_super_area += [
                    household
                    for household in area.households
                    if household.type in ["families", "ya_parents", "nokids"]
                ]
            shuffle(households_super_area)
            for area in super_area.areas:
                if area.care_home is not None:
                    people_in_care_home = [
                        person for person in area.care_home.residents
                    ]
                    for i, person in enumerate(people_in_care_home):
                        household = households_super_area[i]
                        household.residences_to_visit["care_home"] = (
                            *household.residences_to_visit["care_home"],
                            area.care_home,
                        )
                        # Collect data for visualization
                        care_home_link_data.append({
                            "Household ID": household.id,
                            "Household Type": household.type,
                            "Linked Care Home ID": area.care_home.id,
                            "Super Area": super_area.name
                        })
         # Display collected data as a DataFrame for a sample view
        df_care_home_links = pd.DataFrame(care_home_link_data)
        print("\n===== Sample of Linked Households to Care Homes =====")
        #print(df_care_home_links.sample(n=10)) 

    def get_leisure_group(self, person):
        residence_types = list(person.residence.group.residences_to_visit.keys())
        if not residence_types:
            return
        if len(residence_types) == 0:
            which_type = residence_types[0]
        else:
            if self.policy_reductions:
                probabilities = self.policy_reductions
            else:
                probabilities = self.residence_type_probabilities
            residence_type_probabilities = np.array(
                [probabilities[residence_type] for residence_type in residence_types]
            )
            residence_type_probabilities = (
                residence_type_probabilities / residence_type_probabilities.sum()
            )
            type_sample = random_choice_numba(
                tuple(range(len(residence_type_probabilities))),
                residence_type_probabilities,
            )
            which_type = residence_types[type_sample]
        candidates = person.residence.group.residences_to_visit[which_type]
        n_candidates = len(candidates)
        if n_candidates == 0:
            return
        elif n_candidates == 1:
            group = candidates[0]
        else:
            group = candidates[randint(0, n_candidates - 1)]
        return group

    def get_poisson_parameter(
        self, sex, age, day_type, working_hours, region=None, policy_reduction=None
    ):
        """
        This differs from the super() implementation in that we do not allow
        visits during working hours as most people are away.
        """
        if working_hours:
            return 0
        return super().get_poisson_parameter(
            sex=sex,
            age=age,
            day_type=day_type,
            working_hours=working_hours,
            region=region,
            policy_reduction=policy_reduction,
        )