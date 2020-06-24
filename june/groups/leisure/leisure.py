import numpy as np
from numba import jit
import yaml
from typing import List, Dict
from june.demography import Person
from june.demography.geography import Geography
from june.groups.leisure import (
    SocialVenueDistributor,
    PubDistributor,
    GroceryDistributor,
    CinemaDistributor,
    HouseholdVisitsDistributor,
    CareHomeVisitsDistributor,
)
from june.groups.leisure import Pubs, Cinemas, Groceries
from june import paths

default_config_filename = paths.configs_path / "config_example.yaml"


@jit(nopython=True)
def random_choice_numba(arr, prob):
    """
    Fast implementation of np.random.choice
    """
    return arr[np.searchsorted(np.cumsum(prob), np.random.rand(), side="right")]


@jit(nopython=True)
def roll_activity_dice(poisson_parameters, delta_time, n_activities):
    total_poisson_parameter = np.sum(poisson_parameters)
    does_activity = np.random.rand() < (
        1.0 - np.exp(-total_poisson_parameter * delta_time)
    )
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
        if not hasattr(world, "pubs"):
            raise ValueError("Your world does not have pubs.")
        leisure_distributors["pubs"] = PubDistributor.from_config(world.pubs)
    if "cinemas" in list_of_leisure_groups:
        if not hasattr(world, "cinemas"):
            raise ValueError("Your world does not have cinemas.")
        leisure_distributors["cinemas"] = CinemaDistributor.from_config(world.cinemas)
    if "groceries" in list_of_leisure_groups:
        if not hasattr(world, "groceries"):
            raise ValueError("Your world does not have groceries.")
        leisure_distributors["groceries"] = GroceryDistributor.from_config(
            world.groceries
        )
    if "care_home_visits" in list_of_leisure_groups:
        if not hasattr(world, "care_homes"):
            raise ValueError("Your world does not have care homes.")
        leisure_distributors[
            "care_home_visits"
        ] = CareHomeVisitsDistributor.from_config(world.super_areas)
    if "household_visits" in list_of_leisure_groups:
        if not hasattr(world, "households"):
            raise ValueError("Your world does not have households.")
        leisure_distributors[
            "household_visits"
        ] = HouseholdVisitsDistributor.from_config(world.super_areas)
    if "residence_visits" in list_of_leisure_groups:
        raise NotImplementedError

    return Leisure(leisure_distributors)


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

    def distribute_social_venues_to_people(self, people : List[Person]):
        for person in people:
            for activity, distributor in self.leisure_distributors.items():
                social_venues = distributor.get_possible_venues_for_person(person)
                person.social_venues[activity] = social_venues

    def get_leisure_probability_for_age_and_sex(
        self, age, sex, delta_time, is_weekend, closed_venues
    ):
        poisson_parameters = []
        drags_household_probabilities = []
        activities = []
        for activity, distributor in self.leisure_distributors.items():
            drags_household_probabilities.append(
                distributor.drags_household_probability
            )
            if closed_venues is not None and distributor.spec in closed_venues:
                poisson_parameters.append(0.0)
            else:
                poisson_parameters.append(
                    distributor.get_poisson_parameter(sex=sex, age=age, is_weekend=is_weekend)
                )
            activities.append(activity)

        total_poisson_parameter = sum(poisson_parameters)
        does_activity_probability = np.exp(1.0 - delta_time * total_poisson_parameter)
        activities_probabilities = {
            activities[i]: poisson_parameters[i] / total_poisson_parameter
            for i in range(len(activities))
        }
        drags_household_probabilities = {
            activities[i]: drags_household_probabilities[i]
            for i in range(len(activities))
        }
        return {
            "does_activity": does_activity_probability,
            "drags_household": drags_household_probabilities,
            "activities": activities_probabilities,
        }

    def drags_household_to_activity(self, person, activity):
        prob = self.probabilities_by_age_sex[person.sex][person.age]["drags_household"][
            activity
        ]
        return np.random.rand() < prob

    # def assign_social_venue_to_person(self, person, activity):
    #    candidates = person.social_venues[activity]
    #    if len(candidates) == 1:
    #        social_venue = candidates[0]
    #    else:
    #        idx = np.random.randint(0, len(candidates))
    #        social_venue = candidates[idx]
    #    social_venue.add(person, activity="leisure")
    #    return social_venue

    # def send_household_with_person_if_necessary(
    #    self, person, leisure_distributor, social_venue
    # ):
    #    """
    #    When we know that the person does an activity in the social venue X,
    #    then we ask X whether the person needs to drag the household with
    #    him or her.
    #    """
    #    if (
    #        person.residence.group.spec == "care_home"
    #        or person.residence.group.type in ["communal", "other", "student"]
    #    ):
    #        return False
    #    if leisure_distributor.person_drags_household():
    #        for mate in person.residence.group.residents:
    #            if not mate.busy:
    #                social_venue.add(mate, activity="leisure")  # ignores size checking
    #        return True

    def get_subgroup_for_person_and_housemates(self, person: Person):
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
        prob_age_sex = self.probabilities_by_age_sex[person.sex][person.age]
        if np.random.rand() < prob_age_sex["does_activity"]:
            activity_idx = random_choice_numba(
                arr=np.arange(0, len(prob_age_sex["activities"])),
                prob=np.array(list(prob_age_sex["activities"].values())),
            )
            activity = list(prob_age_sex["activities"].keys())[activity_idx]
            candidates = person.social_venues[activity]
            if not candidates:
                return
            if len(candidates) == 1:
                return candidates[0].get_leisure_subgroup(person)
            else:
                idx = np.random.randint(0, len(candidates))
                return candidates[idx].get_leisure_subgroup(person)
        else:
            return 

    def generate_leisure_probabilities_for_timestep(
        self, delta_time, is_weekend, closed_venues
    ):
        men_probs = [
            self.get_leisure_probability_for_age_and_sex(
                age, "m", delta_time, is_weekend, closed_venues
            )
            for age in range(0, 100)
        ]
        women_probs = [
            self.get_leisure_probability_for_age_and_sex(
                age, "f", delta_time, is_weekend, closed_venues
            )
            for age in range(0, 100)
        ]
        self.probabilities_by_age_sex = {}
        self.probabilities_by_age_sex["m"] = men_probs
        self.probabilities_by_age_sex["f"] = women_probs
