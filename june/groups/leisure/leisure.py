import numpy as np
from numba import jit
import yaml
import logging
from random import random, randint
from typing import List, Dict
from june.demography import Person
from june.geography import Geography, SuperAreas, Areas, Regions, Region
from june.groups.leisure import (
    SocialVenueDistributor,
    PubDistributor,
    GroceryDistributor,
    CinemaDistributor,
    ResidenceVisitsDistributor,
    GymDistributor
)
from june.groups.leisure import Pubs, Cinemas, Groceries
from june.groups import Household, ExternalSubgroup, Households
from june.utils import random_choice_numba
from june import paths


default_config_filename = paths.configs_path / "config_example.yaml"

logger = logging.getLogger("leisure")


def generate_leisure_for_world(list_of_leisure_groups, world):
    """
    Generates an instance of the leisure class for the specified geography and leisure groups.

    Parameters
    ----------
    list_of_leisure_groups
        list of names of the lesire groups desired. Ex: ["pubs", "cinemas"]
    """
    leisure_distributors = {}
    if "pubs" in list_of_leisure_groups:
        if not hasattr(world, "pubs") or world.pubs is None or len(world.pubs) == 0:
            logger.warning("No pubs in this world/domain")
        else:
            leisure_distributors["pub"] = PubDistributor.from_config(world.pubs)
    if "gyms" in list_of_leisure_groups:
        if not hasattr(world, "gyms") or world.gyms is None or len(world.gyms) == 0:
            logger.warning("No gyms in this world/domain")
        else:
            leisure_distributors["gym"] = GymDistributor.from_config(world.gyms)
    if "cinemas" in list_of_leisure_groups:
        if (
            not hasattr(world, "cinemas")
            or world.cinemas is None
            or len(world.cinemas) == 0
        ):
            logger.warning("No cinemas in this world/domain")
        else:
            leisure_distributors["cinema"] = CinemaDistributor.from_config(
                world.cinemas
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
                world.groceries
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
        ] = ResidenceVisitsDistributor.from_config()
    leisure = Leisure(leisure_distributors=leisure_distributors, regions=world.regions)
    return leisure


def generate_leisure_for_config(world, config_filename=default_config_filename):
    """
    Generates an instance of the leisure class for the specified geography and leisure groups.
    Parameters
    ----------
    list_of_leisure_groups
        list of names of the lesire groups desired. Ex: ["pubs", "cinemas"]
    """
    with open(config_filename) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    try:
        list_of_leisure_groups = config["activity_to_super_groups"]["leisure"]
    except:
        list_of_leisure_groups = config["activity_to_groups"]["leisure"]
    leisure_instance = generate_leisure_for_world(list_of_leisure_groups, world)
    return leisure_instance


class Leisure:
    """
    Class to manage all possible activites that happen during leisure time.
    """

    def __init__(
        self,
        leisure_distributors: Dict[str, SocialVenueDistributor],
        regions: Regions = None,
    ):
        """
        Parameters
        ----------
        leisure_distributors
            List of social venue distributors.
        """
        self.probabilities_by_region_sex_age = None
        self.leisure_distributors = leisure_distributors
        self.n_activities = len(self.leisure_distributors)
        self.policy_reductions = {}
        self.regions = regions  # needed for regional compliances

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
        for i, area in enumerate(areas):
            if i % 2000 == 0:
                logger.info(f"Distributed in {i} of {len(areas)} areas.")
            for activity, distributor in self.leisure_distributors.items():
                if "visits" in activity:
                    continue
                social_venues = distributor.get_possible_venues_for_area(area)
                if social_venues is not None:
                    area.social_venues[activity] = social_venues
        logger.info(f"Distributed in {len(areas)} of {len(areas)} areas.")

    def generate_leisure_probabilities_for_timestep(
            self, delta_time: float, working_hours: bool, day_type:str,
    ):
        self.probabilities_by_region_sex_age = {}
        if self.regions:
            for region in self.regions:
                self.probabilities_by_region_sex_age[
                    region.name
                ] = self._generate_leisure_probabilities_for_age_and_sex(
                    delta_time=delta_time,
                    working_hours=working_hours,
                    day_type=day_type,
                    region=region,
                )
        else:
            self.probabilities_by_region_sex_age = (
                self._generate_leisure_probabilities_for_age_and_sex(
                    delta_time=delta_time,
                    working_hours=working_hours,
                    day_type=day_type,
                    region=None,
                )
            )

    def get_subgroup_for_person_and_housemates(
        self, person: Person, to_send_abroad: dict = None
    ):
        """
        Main function of the Leisure class. For every possible activity a person can do,
        we chech the Poisson parameter lambda = probability / day * deltat of that activty
        taking place. We then sum up the Poisson parameters to decide whether a person
        does any activity at all. The relative weight of the Poisson parameters gives then
        the specific activity a person does.
        If a person ends up going to a social venue, we do a second check to see if his/her
        entire household accompanies him/her.
        The social venue subgroups are attached to the involved people, but they are not
        added to the subgroups, since it is possible they change their plans if a policy is in
        place or they have other responsibilities.
        The function returns None if no activity takes place.

        Parameters
        ----------
        person
            an instance of person
        """
        if person.residence.group.spec == "care_home":
            return
        prob_age_sex = self._get_activity_probabilities_for_person(person=person)
        if random() < prob_age_sex["does_activity"]:
            activity_idx = random_choice_numba(
                arr=np.arange(0, len(prob_age_sex["activities"])),
                prob=np.array(list(prob_age_sex["activities"].values())),
            )
            activity = list(prob_age_sex["activities"].keys())[activity_idx]
            activity_distributor = self.leisure_distributors[activity]
            subgroup = activity_distributor.get_leisure_subgroup(
                person, to_send_abroad=to_send_abroad
            )
            person.subgroups.leisure = subgroup
            activity_distributor.send_household_with_person_if_necessary(
                person=person, to_send_abroad=to_send_abroad
            )
            return subgroup

    def _generate_leisure_probabilities_for_age_and_sex(
        self,
        delta_time: float,
        working_hours: bool,
        day_type: str,
        region: Region 
    ):
        ret = {}
        for sex in ["m", "f"]:
            probs = [
                self._get_leisure_probability_for_age_and_sex(
                    age=age,
                    sex=sex,
                    delta_time=delta_time,
                    day_type=day_type,
                    working_hours=working_hours,
                    region=region
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
        day_type: str,
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
        activities = []
        for activity, distributor in self.leisure_distributors.items():
            drags_household_probabilities.append(
                distributor.drags_household_probability
            )
            activity_poisson_parameter = self._get_activity_poisson_parameter(
                activity=activity,
                distributor=distributor,
                age=age,
                sex=sex,
                day_type=day_type,
                working_hours=working_hours,
                region=region,
            )
            poisson_parameters.append(activity_poisson_parameter)
            activities.append(activity)
        total_poisson_parameter = sum(poisson_parameters)
        does_activity_probability = 1.0 - np.exp(-delta_time * total_poisson_parameter)
        activities_probabilities = {}
        drags_household_probabilities_dict = {}
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
        return {
            "does_activity": does_activity_probability,
            "drags_household": drags_household_probabilities_dict,
            "activities": activities_probabilities,
        }

    def _get_activity_poisson_parameter(
        self,
        activity: str,
        distributor: SocialVenueDistributor,
        age: int,
        sex: str,
        day_type: str,
        working_hours: bool,
        region: Region,
    ):
        """
        Computes an activity poisson parameter taking into account active policies,
        regional compliances and lockdown tiers.
        """
        if activity in self.policy_reductions:
            policy_reduction = (
                self.policy_reductions[activity][day_type][sex][age]
            )  
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
        return activity_poisson_parameter

    def _drags_household_to_activity(self, person, activity):
        """
        Checks whether the person drags the household to the activity.
        """
        try:
            prob = self.probabilities_by_region_sex_age[person.region.name][person.sex][
                person.age
            ]["drags_household"][activity]
        except KeyError:
            prob = self.probabilities_by_region_sex_age[person.sex][person.age][
                "drags_household"
            ][activity]
        except AttributeError:
            if person.sex in self.probabilities_by_region_sex_age:
                prob = self.probabilities_by_region_sex_age[person.sex][person.age][
                    "drags_household"
                ][activity]
            else:
                prob = self.probabilities_by_region_sex_age[
                    list(self.probabilities_by_region_sex_age.keys())[0]
                ][person.sex][person.age]["drags_household"][activity]
        return random() < prob

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

