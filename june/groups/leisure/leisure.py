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
    leisure = Leisure(leisure_distributors)
    leisure.distribute_social_venues_to_people(world.people)
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
        self.refresh_random_numbers()

    def refresh_random_numbers(self):
        self.random_integers = list(np.random.randint(0, 2000, 10_000_000))
        self.random_numbers = list(np.random.rand(10_000_000))

    def get_random_number(self):
        try:
            return self.random_numbers.pop()
        except IndexError:
            self.refresh_random_numbers()
            return self.random_numbers.pop()

    def get_random_integer(self):
        try:
            return self.random_integers.pop()
        except IndexError:
            self.refresh_random_numbers()
            return self.random_integers.pop()

    def distribute_social_venues_to_people(self, people: List[Person]):
        for person in people:
            person.social_venues = {}
            for activity, distributor in self.leisure_distributors.items():
                social_venues = distributor.get_possible_venues_for_person(person)
                person.social_venues[activity] = social_venues

    def update_household_and_care_home_visits_targets(self, people: List[Person]):
        """
        Updates the candidates to go for visiting households and care homes.
        This is necessary in case the relatives have died.
        """
        for person in people:
            if "household_visits" in person.social_venues:
                person.social_venues["household_visits"] = self.leisure_distributors[
                    "household_visits"
                ].get_possible_venues_for_person(person)
            if "care_home_visits" in person.social_venues:
                person.social_venues["care_home_visits"] = self.leisure_distributors[
                    "care_home_visits"
                ].get_possible_venues_for_person(person)

    def get_leisure_probability_for_age_and_sex(
        self, age, sex, delta_time, is_weekend, closed_venues
    ):
        """
        Computes the probabilities of going to different leisure activities,
        and dragging the household with the person that does the activity.
        """
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
        return self.get_random_number() < prob

    def send_household_with_person_if_necessary(
        self, person, subgroup, probability,
    ):
        """
        When we know that the person does an activity in the social venue X,
        then we ask X whether the person needs to drag the household with
        him or her.
        """
        if (
            person.residence.group.spec == "care_home"
            or person.residence.group.type in ["communal", "other", "student"]
        ):
            return 
        if self.get_random_number() < probability:
            for mate in person.residence.group.residents:
                if mate != person:
                    if mate.busy:
                        if mate.leisure is not None: #this perosn has already been assigned somewhere
                            mate.leisure.remove(mate)
                            mate.subgroups.leisure = subgroup
                            subgroup.append(mate)
                    else:
                        mate.subgroups.leisure = subgroup #person will be added later in the simulator.

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
        if self.get_random_number() < prob_age_sex["does_activity"]:
            activity_idx = random_choice_numba(
                arr=np.arange(0, len(prob_age_sex["activities"])),
                prob=np.array(list(prob_age_sex["activities"].values())),
            )
            activity = list(prob_age_sex["activities"].keys())[activity_idx]
            candidates = person.social_venues[activity]
            candidates_length = len(candidates)
            if candidates_length == 0:
                return
            if candidates_length == 1:
                subgroup = candidates[0].get_leisure_subgroup(person)
            else:
                idx = self.get_random_integer() % candidates_length
                subgroup = candidates[idx].get_leisure_subgroup(person)
            self.send_household_with_person_if_necessary(
                person, subgroup, prob_age_sex["drags_household"][activity]
            )
            person.subgroups.leisure = subgroup
            return subgroup

    def generate_leisure_probabilities_for_timestep(
        self, delta_time, is_weekend, closed_venues=None
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
