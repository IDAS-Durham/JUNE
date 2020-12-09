import numpy as np
import pandas as pd
import yaml
from random import randint, shuffle, random
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
        poisson_parameters: dict = None,
        neighbours_to_consider=None,
        maximum_distance=None,
        weekend_boost: float = 2.0,
        drags_household_probability=1.0,
    ):
        super().__init__(
            social_venues=None,
            poisson_parameters=poisson_parameters,
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
                    if household.type != "communal"
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
                    household.residences_to_visit["household"] = tuple(
                        households_to_visit
                    )

    def get_social_venue_for_person(self, person):
        households_to_visit = person.residence.group.residences_to_visit["household"]
        if households_to_visit is None:
            return None
        return households_to_visit[randint(0, len(households_to_visit) - 1)]

    def get_leisure_subgroup_type(self, person):
        """
        A person wants to come and visit this household. We need to assign the person
        to the relevant age subgroup, and make sure the residents welcome him and
        don't go do any other leisure activities.
        """
        return Household.get_leisure_subgroup_type(person)

    def get_poisson_parameter(
        self,
        sex,
        age,
        is_weekend: bool = False,
        policy_poisson_parameter=None,
        region=None,
    ):
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
        if region is None:
            regional_compliance = 1
        else:
            regional_compliance = region.regional_compliance
            if self.spec in region.closed_venues:
                if random() < regional_compliance:
                    return 0
        original_poisson_parameter = self.poisson_parameters[sex][age]
        original_poisson_parameter = (
            original_poisson_parameter * self.get_weekend_boost(is_weekend)
        )
        if policy_poisson_parameter is None:
            return original_poisson_parameter
        
        poisson_parameter = original_poisson_parameter + regional_compliance * (
            policy_poisson_parameter - original_poisson_parameter
        )
        return poisson_parameter
