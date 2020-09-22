import numpy as np
from numba import jit
import yaml
import logging
from random import random, sample
from typing import List, Dict
from june.demography import Person
from june.geography import Geography, SuperAreas, Areas
from june.groups.leisure import (
    SocialVenueDistributor,
    PubDistributor,
    GroceryDistributor,
    CinemaDistributor,
    HouseholdVisitsDistributor,
    CareHomeVisitsDistributor,
)
from june.groups.leisure import Pubs, Cinemas, Groceries
from june.groups import Household, ExternalSubgroup, Households
from june.utils import random_choice_numba
from june import paths


default_config_filename = paths.configs_path / "config_example.yaml"

logger = logging.getLogger(__name__)


@jit(nopython=True)
def roll_activity_dice(poisson_parameters, delta_time, n_activities):
    total_poisson_parameter = np.sum(poisson_parameters)
    does_activity = random() < (1.0 - np.exp(-total_poisson_parameter * delta_time))
    if does_activity:
        poisson_parameters_normalized = poisson_parameters / total_poisson_parameter
        return random_choice_numba(
            np.arange(0, n_activities), poisson_parameters_normalized
        )
    return None


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
            leisure_distributors["pubs"] = PubDistributor.from_config(world.pubs)
    if "cinemas" in list_of_leisure_groups:
        if (
            not hasattr(world, "cinemas")
            or world.cinemas is None
            or len(world.cinemas) == 0
        ):
            logger.warning("No cinemas in this world/domain")
        else:
            leisure_distributors["cinemas"] = CinemaDistributor.from_config(
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
            leisure_distributors["groceries"] = GroceryDistributor.from_config(
                world.groceries
            )
    if "care_home_visits" in list_of_leisure_groups:
        if not hasattr(world, "care_homes"):
            raise ValueError("Your world does not have care homes.")
        leisure_distributors[
            "care_home_visits"
        ] = CareHomeVisitsDistributor.from_config()
    if "household_visits" in list_of_leisure_groups:
        if not hasattr(world, "households"):
            raise ValueError("Your world does not have households.")
        leisure_distributors[
            "household_visits"
        ] = HouseholdVisitsDistributor.from_config()
    leisure = Leisure(leisure_distributors)
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

    def __init__(self, leisure_distributors: Dict[str, SocialVenueDistributor]):
        """
        Parameters
        ----------
        leisure_distributors
            List of social venue distributors.
        """
        self.probabilities_by_age_sex = None
        self.leisure_distributors = leisure_distributors
        self.n_activities = len(self.leisure_distributors)
        self.closed_venues = set()

    def distribute_social_venues_to_areas(self, areas: Areas, super_areas: SuperAreas):
        logger.info("Linking households for visits")
        if "household_visits" in self.leisure_distributors:
            self.leisure_distributors["household_visits"].link_households_to_households(
                super_areas
            )
        logger.info("Done")
        logger.info("Linking households with care homes for visits")
        if "care_home_visits" in self.leisure_distributors:
            self.leisure_distributors["care_home_visits"].link_households_to_care_homes(
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

    def update_household_and_care_home_visits_targets(self, people: List[Person]):
        """
        Updates the candidates to go for visiting households and care homes.
        This is necessary in case the relatives have died.
        """
        for person in people:
            if person.residence is None or person.residence.group.spec != "household":
                continue
            if "household_visits" in person.residence.group.social_venues:
                person.residence.group.social_venues[
                    "household_visits"
                ] = self.leisure_distributors[
                    "household_visits"
                ].get_possible_venues_for_household(
                    person.residence.group
                )
            if "care_home_visits" in person.residence.group.social_venues:
                person.residence.group.social_venues[
                    "care_home_visits"
                ] = self.leisure_distributors[
                    "care_home_visits"
                ].get_possible_venues_for_household(
                    person.residence.group
                )

    def get_leisure_probability_for_age_and_sex(
        self, age, sex, delta_time, is_weekend, working_hours
    ):
        """
        Computes the probabilities of going to different leisure activities,
        and dragging the household with the person that does the activity.
        """
        poisson_parameters = []
        drags_household_probabilities = []
        activities = []
        for activity, distributor in self.leisure_distributors.items():
            if (
                activity == "household_visits" and working_hours
            ) or distributor.spec in self.closed_venues:
                # we do not have household visits during working hours as most households by then.
                continue
            drags_household_probabilities.append(
                distributor.drags_household_probability
            )
            poisson_parameters.append(
                distributor.get_poisson_parameter(
                    sex=sex, age=age, is_weekend=is_weekend
                )
            )
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

    def drags_household_to_activity(self, person, activity):
        prob = self.probabilities_by_age_sex[person.sex][person.age]["drags_household"][
            activity
        ]
        return random() < prob

    def send_household_with_person_if_necessary(
        self, person, subgroup, probability, to_send_abroad=None
    ):
        """
        When we know that the person does an activity in the social venue X,
        then we ask X whether the person needs to drag the household with
        him or her.
        """
        # this produces a recursive import...
        if (
            person.residence.group.spec == "care_home"
            or person.residence.group.type in ["communal", "other", "student"]
        ):
            return
        assert subgroup is not None
        if random() < probability:
            for mate in person.residence.group.residents:
                if mate != person:
                    if mate.busy:
                        if (
                            mate.leisure is not None
                        ):  # this perosn has already been assigned somewhere
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
                            if not subgroup.external:
                                subgroup.append(mate)
                            else:
                                to_send_abroad.add_person(mate, subgroup)
                    mate.subgroups.leisure = (
                        subgroup  # person will be added later in the simulator.
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
        if person.residence.group.spec != "household":
            return
        prob_age_sex = self.probabilities_by_age_sex[person.sex][person.age]
        if random() < prob_age_sex["does_activity"]:
            activity_idx = random_choice_numba(
                arr=np.arange(0, len(prob_age_sex["activities"])),
                prob=np.array(list(prob_age_sex["activities"].values())),
            )
            activity = list(prob_age_sex["activities"].keys())[activity_idx]
            activity_distributor = self.leisure_distributors[activity]
            leisure_subgroup_type = activity_distributor.get_leisure_subgroup_type(
                person
            )
            if activity == "household_visits":
                candidates = person.residence.group.households_to_visit
                if candidates is None:
                    return
            elif activity == "care_home_visits":
                candidates = person.residence.group.care_homes_to_visit
                if candidates is None:
                    return
            else:
                candidates = person.area.social_venues[activity]
            candidates_length = len(candidates)
            if candidates_length == 0:
                return
            elif candidates_length == 1:
                group = candidates[0]
            else:
                indices = sample(range(len(candidates)), len(candidates))
                for idx in indices:
                    group = candidates[idx]
                    if group is not None:
                        break
            if group is None:
                return
            elif group.external:
                subgroup = ExternalSubgroup(
                    subgroup_type=leisure_subgroup_type, group=group
                )
            else:
                subgroup = group[leisure_subgroup_type]
            assert subgroup is not None
            self.send_household_with_person_if_necessary(
                person,
                subgroup,
                prob_age_sex["drags_household"][activity],
                to_send_abroad=to_send_abroad,
            )
            if activity == "household_visits":
                group.make_household_residents_stay_home(to_send_abroad=to_send_abroad)
            person.subgroups.leisure = subgroup
            return subgroup

    def generate_leisure_probabilities_for_timestep(
        self, delta_time: float, working_hours: bool, is_weekend: bool
    ):
        men_probs = [
            self.get_leisure_probability_for_age_and_sex(
                age=age,
                sex="m",
                delta_time=delta_time,
                is_weekend=is_weekend,
                working_hours=working_hours,
            )
            for age in range(0, 100)
        ]
        women_probs = [
            self.get_leisure_probability_for_age_and_sex(
                age=age,
                sex="f",
                delta_time=delta_time,
                is_weekend=is_weekend,
                working_hours=working_hours,
            )
            for age in range(0, 100)
        ]
        self.probabilities_by_age_sex = {}
        self.probabilities_by_age_sex["m"] = men_probs
        self.probabilities_by_age_sex["f"] = women_probs
