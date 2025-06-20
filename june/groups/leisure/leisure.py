import numpy as np
import yaml
import logging
import pandas as pd
from random import random
from typing import Dict, List
from june.demography import Person
from june.geography import SuperAreas, Areas, Regions, Region
from june.groups.leisure import (
    SocialVenueDistributor,
    PubDistributor,
    GroceryDistributor,
    CinemaDistributor,
    ResidenceVisitsDistributor,
    GymDistributor,
)
from june.groups.leisure.friend_invitations import FriendInvitationManager
from june.utils import random_choice_numba
from june import paths
from june.utils.parse_probabilities import parse_opens
from june.mpi_wrapper import mpi_comm, mpi_rank, mpi_size, MPI, mpi_available

# Rank prefix for all prints
RANK_PREFIX = f"[RANK {mpi_rank}]" if mpi_available else "[RANK 0]"


default_config_filename = paths.configs_path / "config_simulation.yaml"

logger = logging.getLogger("leisure")


def generate_leisure_for_world(list_of_leisure_groups, world, daytypes, contact_manager=None):
    """
    Generates an instance of the leisure class for the specified geography and leisure groups.

    Parameters
    ----------
    list_of_leisure_groups
        list of names of the leisure groups desired. Ex: ["pubs", "cinemas"]
    contact_manager
        ContactManager instance for recording temporary contacts
    """
    leisure_distributors = {}
    if "pubs" in list_of_leisure_groups:
        if not hasattr(world, "pubs") or world.pubs is None or len(world.pubs) == 0:
            logger.warning("No pubs in this world/domain")
        else:
            leisure_distributors["pub"] = PubDistributor.from_config(
                world.pubs, daytypes=daytypes
            )
    if "gyms" in list_of_leisure_groups:
        if not hasattr(world, "gyms") or world.gyms is None or len(world.gyms) == 0:
            logger.warning("No gyms in this world/domain")
        else:
            leisure_distributors["gym"] = GymDistributor.from_config(
                world.gyms, daytypes=daytypes
            )
    if "cinemas" in list_of_leisure_groups:
        if (
            not hasattr(world, "cinemas")
            or world.cinemas is None
            or len(world.cinemas) == 0
        ):
            logger.warning("No cinemas in this world/domain")
        else:
            leisure_distributors["cinema"] = CinemaDistributor.from_config(
                world.cinemas, daytypes=daytypes
            )
    if "groceries" in list_of_leisure_groups:
        if (
            not hasattr(world, "groceries")
            or world.groceries is None
            or len(world.groceries) == 0
        ):
            logger.warning("No groceries in this world/domain")
        else:
            leisure_distributors["grocery"] = GroceryDistributor.from_config(
                world.groceries, daytypes=daytypes
            )
    if (
        "household_visits" in list_of_leisure_groups
        or "care_home_visits" in list_of_leisure_groups
    ):
        if not hasattr(world, "care_homes") or not hasattr(world, "households"):
            raise ValueError(
                "Your world does not have care homes or households for visits."
            )
        leisure_distributors[
            "residence_visits"
        ] = ResidenceVisitsDistributor.from_config(daytypes=daytypes)
    leisure = Leisure(leisure_distributors=leisure_distributors, regions=world.regions, contact_manager=contact_manager)
    return leisure


def generate_leisure_for_config(world, config_filename=default_config_filename, contact_manager=None):
    """
    Generates an instance of the leisure class for the specified geography and leisure groups.
    Parameters
    ----------
    list_of_leisure_groups
        list of names of the lesire groups desired. Ex: ["pubs", "cinemas"]
    contact_manager
        ContactManager instance for recording temporary contacts
    """
    with open(config_filename) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    try:
        list_of_leisure_groups = config["activity_to_super_groups"]["leisure"]
    except Exception:
        list_of_leisure_groups = config["activity_to_groups"]["leisure"]

    if "weekday" in config.keys() and "weekend" in config.keys():
        daytypes = {"weekday": config["weekday"], "weekend": config["weekend"]}
    else:
        daytypes = {
            "weekday": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "weekend": ["Saturday", "Sunday"],
        }
    leisure_instance = generate_leisure_for_world(
        list_of_leisure_groups, world, daytypes, contact_manager=contact_manager
    )
    return leisure_instance


class Leisure:
    """
    Class to manage all possible activites that happen during leisure time.
    """

    def __init__(
        self,
        leisure_distributors: Dict[str, SocialVenueDistributor],
        regions: Regions = None,
        contact_manager=None
        ):
        """
        Parameters
        ----------
        leisure_distributors
            List of social venue distributors.
        contact_manager
            ContactManager instance for recording temporary contacts
        """
        self.probabilities_by_region_sex_age = None
        self.leisure_distributors = leisure_distributors
        self.n_activities = len(self.leisure_distributors)
        self.policy_reductions = {}
        self.regions = regions  # needed for regional compliances
        self.friend_invitation_manager = FriendInvitationManager(contact_manager=contact_manager)
    
    def set_contact_manager(self, contact_manager):
        """
        Set or update the contact manager for recording temporary contacts.
        
        Parameters
        ----------
        contact_manager
            ContactManager instance for recording temporary contacts
        """
        self.friend_invitation_manager.contact_manager = contact_manager

    def distribute_social_venues_to_areas(self, areas: Areas, super_areas: SuperAreas):
        logger.info("Linking households and care homes for visits")
        if "residence_visits" in self.leisure_distributors:
            self.leisure_distributors["residence_visits"].link_households_to_households(
                super_areas
            )
            self.leisure_distributors["residence_visits"].link_households_to_care_homes(
                super_areas
            )
        logger.info("Done")
        logger.info("Distributing social venues to areas")
        # Collect data for visualization
        distributed_venues_data = []
        
        for i, area in enumerate(areas):
            if i % 2000 == 0:
                logger.info(f"Distributed in {i} of {len(areas)} areas.")
            
            for activity, distributor in self.leisure_distributors.items():
                if "visits" in activity:
                    continue
                
                social_venues = distributor.get_possible_venues_for_area(area)
                if social_venues is not None:
                    area.social_venues[activity] = social_venues
                    
                    # Collect data for each assigned venue in this area
                    for venue in social_venues:
                        distributed_venues_data.append({
                            "Area name": area.name,
                            "Activity Type": activity,
                            "Assigned Venue ID": venue.id,
                            "Assigned Venue Coordinates": venue.coordinates,
                            "Area of Assigned Venue": venue.area.name if venue.area else "None"
                        })
        
        logger.info(f"Distributed in {len(areas)} of {len(areas)} areas.")
        
        # Convert collected data to DataFrame for visualization
        df_distributed_venues = pd.DataFrame(distributed_venues_data)
        print("\n===== Sample of Distributed Social Venues to Areas =====")
        print(df_distributed_venues)  # Show a random sample of 10 assigned venues

    def generate_leisure_probabilities_for_timestep(
        self, delta_time: float, working_hours: bool, date: str
    ):
        
        self.probabilities_by_region_sex_age = {}

        if self.regions:
            for region in self.regions:
                probabilities = self._generate_leisure_probabilities_for_age_and_sex(
                    delta_time=delta_time,
                    working_hours=working_hours,
                    date=date,
                    region=region,
                )
                self.probabilities_by_region_sex_age[region.name] = probabilities
        else:
            self.probabilities_by_region_sex_age = (
                self._generate_leisure_probabilities_for_age_and_sex(
                    delta_time=delta_time,
                    working_hours=working_hours,
                    date=date,
                    region=None,
                )
            )

    def get_subgroup_for_person_and_housemates(
        self, person: Person, to_send_abroad: dict = None
    ):
        """
        Main function of the Leisure class. For every possible activity a person can do,
        we check the Poisson parameter lambda = probability / day * deltat of that activity
        taking place. We then sum up the Poisson parameters to decide whether a person
        does any activity at all. The relative weight of the Poisson parameters gives then
        the specific activity a person does.
        """

        age_before = person.age
        age = person.age
        person.age = age

        if person.residence.group.spec == "care_home":
            person.age = age_before
            return None

        # Calculate probabilities for activities
        prob_age_sex = self._get_activity_probabilities_for_person(person=person)

        # Check if the person does any activity
        if random() < prob_age_sex["does_activity"]:
            # Select activity based on probabilities
            activity_idx = random_choice_numba(
                arr=np.arange(0, len(prob_age_sex["activities"])),
                prob=np.array(list(prob_age_sex["activities"].values())),
            )
            activity = list(prob_age_sex["activities"].keys())[activity_idx]

            # Get the subgroup for the chosen activity
            activity_distributor = self.leisure_distributors[activity]
            subgroup = activity_distributor.get_leisure_subgroup(
                person, to_send_abroad=to_send_abroad
            )
            
            
            # Assign the subgroup to the person
            person.subgroups.leisure = subgroup

            person.age = age_before
            return subgroup

        person.age = age_before
        return None
    
    
    def _generate_leisure_probabilities_for_age_and_sex(
        self, delta_time: float, working_hours: bool, date: str, region: Region
    ):
        ret = {}
        for sex in ["m", "f"]:
            probs = [
                self._get_leisure_probability_for_age_and_sex(
                    age=age,
                    sex=sex,
                    delta_time=delta_time,
                    date=date,
                    working_hours=working_hours,
                    region=region,
                )
                for age in range(0, 100)
            ]
            ret[sex] = probs
        return ret

    def _get_leisure_probability_for_age_and_sex(
        self,
        age: int,
        sex: str,
        delta_time: float,
        date: str,
        working_hours: bool,
        region: Region,
    ):
        """
        Computes the probabilities of going to different leisure activities,
        and dragging the household with the person that does the activity.
        When policies are present, then the regional leisure poisson parameters are
        changed according to the present policy poisson parameter (lambda_2) and the local
        regional compliance like so:
        $ lambda = lambda_1 + regional_compliance * (lambda_2 - lambda_1) $
        where lambda_1 is the original poisson parameter.
        lockdown tier: 1,2,3 - has different implications for leisure:
            1: do nothing
            2: stop household-to-household probability with regional compliance and
               reduce pub probability by 20% - conservative to account for the serving of meals
            3: stop household-to-household probability with regional compliance and
               reduce pub and cinema probability to 0 to simulate closure
        """
        poisson_parameters = []
        drags_household_probabilities = []
        invites_friends_probabilities = []
        activities = []
        for activity, distributor in self.leisure_distributors.items():
            drags_household_probabilities.append(
                distributor.drags_household_probability
            )
            invites_friends_probabilities.append(
                distributor.invites_friends_probability
            )

            activity_poisson_parameter = self._get_activity_poisson_parameter(
                activity=activity,
                distributor=distributor,
                age=age,
                sex=sex,
                date=date,
                working_hours=working_hours,
                region=region,
            )
            poisson_parameters.append(activity_poisson_parameter)
            activities.append(activity)
        

        total_poisson_parameter = sum(poisson_parameters)
        does_activity_probability = 1.0 - np.exp(-delta_time * total_poisson_parameter)
        activities_probabilities = {}
        drags_household_probabilities_dict = {}
        invites_friends_probabilities_dict = {}
        for i in range(len(activities)):
            if poisson_parameters[i] == 0:
                activities_probabilities[activities[i]] = 0
            else:
                activities_probabilities[activities[i]] = (
                    poisson_parameters[i] / total_poisson_parameter
                )
            drags_household_probabilities_dict[
                activities[i]
            ] = drags_household_probabilities[i]
            invites_friends_probabilities_dict[
                activities[i]
            ]  = invites_friends_probabilities[i]


        return {
            "does_activity": does_activity_probability,
            "drags_household": drags_household_probabilities_dict,
            "invites_friends": invites_friends_probabilities_dict,
            "activities": activities_probabilities,
        }

    def _get_activity_poisson_parameter(
        self,
        activity: str,
        distributor: SocialVenueDistributor,
        age: int,
        sex: str,
        date: str,
        working_hours: bool,
        region: Region,
    ):
        """
        Computes an activity poisson parameter taking into account active policies,
        regional compliances and lockdown tiers.
        """
        day = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ][date.weekday()]
        if day in distributor.daytypes["weekday"]:
            day_type = "weekday"
        elif day in distributor.daytypes["weekend"]:
            day_type = "weekend"

        # TODO check closures etc!
        open_times = parse_opens(distributor.open)[day_type]
        open = 1
        if open_times[1] - open_times[0] == 0:
            open = 0
        if date.hour < open_times[0] or date.hour >= open_times[1]:
            open = 0

        if activity in self.policy_reductions:
            policy_reduction = self.policy_reductions[activity][day_type][sex][age]
        else:
            policy_reduction = 1

        activity_poisson_parameter = distributor.get_poisson_parameter(
            sex=sex,
            age=age,
            day_type=day_type,
            working_hours=working_hours,
            policy_reduction=policy_reduction,
            region=region,
        )
        return activity_poisson_parameter * open


    # TESTING TODO
    ######################################################################
    def P_IsAdult(self, age):
        tanh_halfpeak_age = 15  # 17.1
        tanh_width = 0.7  # 1

        minageadult = 13
        maxagechild = 17
        if age < minageadult:
            return 0
        elif age > maxagechild:
            return 1
        else:
            return (np.tanh(tanh_width * (age - tanh_halfpeak_age)) + 1) / 2

    def P_IsChild(self, age):
        return 1 - self.P_IsAdult(age)

    def AorC(self, age):
        r = np.random.rand(1)[0]
        if r < self.P_IsAdult(age):
            return "Adult"
        else:
            return "Child"

    ######################################################################

    def _get_activity_probabilities_for_person(self, person: Person):

        try:
            return self.probabilities_by_region_sex_age[person.region.name][person.sex][
                person.age
            ]
        except KeyError:
            return self.probabilities_by_region_sex_age[person.sex][person.age]
        except AttributeError:
            if person.sex in self.probabilities_by_region_sex_age:
                return self.probabilities_by_region_sex_age[person.sex][person.age]
            else:
                return self.probabilities_by_region_sex_age[
                    list(self.probabilities_by_region_sex_age.keys())[0]
                ][person.sex][person.age]
    
    def process_friend_invitations(self, potential_inviters: List[Person], world) -> None:
        """
        Process friend invitations for leisure activities.
        
        This method handles the complete friend invitation process:
        1. Generate invitations from people who won the invite lottery
        2. Exchange invitations via MPI
        3. Process received invitations and generate responses
        4. Exchange responses via MPI
        5. Apply friend assignments
        
        Parameters
        ----------
        potential_inviters : List[Person]
            People who are doing leisure activities and might invite friends
        world : World
            The simulation world containing all people
        """

        # Clear previous round's data
        self.friend_invitation_manager.clear()
        
        # Step 1: Generate invitations (including delegations for external inviters)
        # We need to pass the activity distributors to the invitation manager
        self._enhance_potential_inviters(potential_inviters)

        self.friend_invitation_manager.generate_invitations(potential_inviters)
        
        # Step 1.5: Exchange delegations for external inviters
        self.friend_invitation_manager.exchange_delegations()
        
        # Step 1.6: Process delegations at venue ranks
        self.friend_invitation_manager.process_delegations()
        
        # Step 2: Exchange invitations via MPI
        self.friend_invitation_manager.exchange_invitations()
        
        # Step 3: Process received invitations
        self.friend_invitation_manager.process_invitations(potential_inviters)
        
        # Step 4: Exchange responses via MPI
        self.friend_invitation_manager.exchange_responses()
        
        # Step 5: Apply friend assignments
        self.friend_invitation_manager.apply_friend_assignments(world)
        
        # Step 6: Cleanup
        self.friend_invitation_manager.cleanup_temporary_attributes(world)
            
    def _enhance_potential_inviters(self, potential_inviters: List[Person]) -> None:
        """
        Add activity distributor references to people's leisure subgroups.
        Now also detects and classifies external inviters for future delegation.
        
        This allows the friend invitation manager to access the invites_friends_probability.
        
        Parameters
        ----------
        potential_inviters : List[Person]
            People who are doing leisure activities
        """        
        # Create activity type aliases to handle mismatches
        activity_aliases = {
            'household': 'residence_visits',  # household visits -> residence_visits distributor
            'care_home': 'residence_visits',  # care home visits -> residence_visits distributor
            'gyms': 'gym',  # plural -> singular
            'pubs': 'pub',  # plural -> singular
            'cinemas': 'cinema',  # plural -> singular
            'groceries': 'grocery',  # plural -> singular
        }
        
        enhanced_count = 0
        external_inviter_count = 0
        activity_type_counts = {}
        external_activity_counts = {}
        external_inviter_ids = set()  # Track external inviters by ID instead of marking Person objects
        
        for i, person in enumerate(potential_inviters):
            if person.subgroups.leisure is not None:
                # Classify external vs local inviters
                if hasattr(person.subgroups.leisure, 'external') and person.subgroups.leisure.external:
                    # Handle external inviters differently
                    external_inviter_count += 1
                    activity_type = person.subgroups.leisure.spec
                    external_activity_counts[activity_type] = external_activity_counts.get(activity_type, 0) + 1
                    
                    # Track external inviter ID instead of marking the Person object
                    external_inviter_ids.add(person.id)
                    continue
                else:
                    # Existing local inviter logic
                    activity_type = person.subgroups.leisure.spec
                    
                    # Count activity types for debugging
                    activity_type_counts[activity_type] = activity_type_counts.get(activity_type, 0) + 1
                    
                    # Try direct match first, then aliases
                    distributor_key = activity_type
                    if distributor_key not in self.leisure_distributors and activity_type in activity_aliases:
                        distributor_key = activity_aliases[activity_type]
                    
                    if distributor_key in self.leisure_distributors:
                        # Add reference to activity distributor
                        person.subgroups.leisure._activity_distributor = self.leisure_distributors[distributor_key]
                        enhanced_count += 1

        # Store external inviter IDs in the friend invitation manager
        self.friend_invitation_manager.external_inviter_ids = external_inviter_ids
        
        
    def _prepare_external_invitation_delegation(self, person: Person) -> dict:
        """
        Prepare delegation data for external inviters.
        
        Parameters
        ----------
        person : Person
            Person with external leisure subgroup
            
        Returns
        -------
        dict or None
            Delegation info or None if person shouldn't invite friends.
        """
        if not (hasattr(person.subgroups.leisure, 'external') and person.subgroups.leisure.external):
            return None
            
        # Extract venue information from external subgroup
        external_group = person.subgroups.leisure.group
        venue_rank = external_group.domain_id
        venue_id = external_group.id
        activity_type = external_group.spec
        
        return {
            'inviter_id': person.id,
            'inviter_home_rank': person._home_rank,
            'venue_rank': venue_rank,
            'venue_id': venue_id,
            'activity_type': activity_type,
            'subgroup_type': person.subgroups.leisure.subgroup_type
        }