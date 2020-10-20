import numpy as np
import pandas as pd
import yaml
from random import randint, shuffle
from june.geography import Areas, SuperAreas
from june.groups import Households

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path
from june.groups import Household

default_config_filename = configs_path / "defaults/groups/leisure/household_visits.yaml"


class HouseholdVisitsDistributor(SocialVenueDistributor):
    def __init__(
        self,
        male_age_probabilities: dict = None,
        female_age_probabilities: dict = None,
        neighbours_to_consider=None,
        maximum_distance=None,
        weekend_boost: float = 2.0,
        drags_household_probability=1.0,
    ):
        super().__init__(
            social_venues=None,
            male_age_probabilities=male_age_probabilities,
            female_age_probabilities=female_age_probabilities,
            neighbours_to_consider=neighbours_to_consider,
            maximum_distance=maximum_distance,
            weekend_boost=weekend_boost,
            drags_household_probability=drags_household_probability,
        )

    @classmethod
    def from_config(cls, config_filename: str = default_config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(**config)

    def link_households_to_households(self, super_areas):
        """
        Links people between households. Strategy: We pair each household with 0, 1, or 2 other households (with equal prob.). The household of the former then has a probability of visiting the household of the later 
        at every time step.

        Parameters
        ----------
        super_areas
            list of super areas
        """
        for super_area in super_areas:
            households_super_area = []
            for area in super_area.areas:
                households_super_area += [
                    household
                    for household in area.households
                    if household.type
                    in [
                        "family",
                        "ya_parents",
                        "nokids",
                        "old",
                        "student",
                        "young_adults",
                    ]
                ]
                shuffle(households_super_area)
            for household in households_super_area:
                if household.size == 0:
                    continue
                households_to_link_n = randint(1, 3)
                households_to_visit = []
                for _ in range(households_to_link_n):
                    house_idx = randint(0, len(households_super_area) - 1)
                    house = households_super_area[house_idx]
                    if house.id == household.id:
                        continue
                    if not house.people:
                        continue
                    person_idx = randint(0, len(house.people) - 1)
                    households_to_visit.append(house)
                if households_to_visit:
                    household.residences_to_visit["household"] = tuple(households_to_visit)

    def get_possible_venues_for_household(self, household: Household):
        """
        Note: This should check if a relative is dead. However, the possible venues for a household
        are decided at the beginning of the simulation for performance. So this is not really checked,
        currently. It shouldn't matter too much, as not that many people die (hopefully).
        """
        if household.relatives_in_households is None:
            return ()
        return tuple(
            relative.residence.group
            for relative in household.relatives_in_households
            if relative.dead is False
        )

    def get_social_venue_for_person(self, person):
        households_to_visit = person.residence.group.residences_to_visit["household"]
        if households_to_visit is None:
            return None
        return households_to_visit[
            randint(0, len(households_to_visit) - 1)
        ]

    def get_poisson_parameter(self, sex, age, is_weekend: bool = False):
        """
        Poisson parameter (lambda) of a person going to one social venue according to their
        age and sex and the distribution of visitors in the venue.

        Parameters
        ----------
        person
            an instance of Person
        delta_t
            interval of time in units of days
        is_weekend
            whether it is a weekend or not
        """
        if sex == "m":
            probability = self.male_probabilities[age]
        else:
            probability = self.female_probabilities[age]
        if is_weekend:
            probability = probability * self.weekend_boost
        return probability

    def get_leisure_subgroup_type(self, person):
        """
        A person wants to come and visit this household. We need to assign the person
        to the relevant age subgroup, and make sure the residents welcome him and
        don't go do any other leisure activities.
        """
        if person.age < 18:
            return Household.SubgroupType.kids
        elif person.age <= 35:
            return Household.SubgroupType.young_adults
        elif person.age < 65:
            return Household.SubgroupType.adults
        else:
            return Household.SubgroupType.old_adults
