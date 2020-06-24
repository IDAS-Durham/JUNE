import numpy as np
import pandas as pd
import yaml
from typing import List, Optional
from june.demography.geography import Areas, SuperAreas
from june.groups import CareHomes, Households

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path

default_config_filename = configs_path / "defaults/groups/leisure/care_home_visits.yaml"


class CareHomeVisitsDistributor(SocialVenueDistributor):
    def __init__(
        self,
        super_areas: SuperAreas,
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
        self.link_households_to_care_homes(super_areas)

    @classmethod
    def from_config(
        cls, super_areas: SuperAreas, config_filename: str = default_config_filename
    ):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(super_areas, **config)

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
        for super_area in super_areas:
            households_super_area = []
            for area in super_area.areas:
                households_super_area += [
                    household
                    for household in area.households
                    if household.type in ["families", "ya_parents", "nokids"]
                ]
                np.random.shuffle(households_super_area)
            for area in super_area.areas:
                if area.care_home is not None:
                    people_in_care_home = [
                        person for person in area.care_home.residents
                    ]
                    for i, person in enumerate(people_in_care_home):
                        if households_super_area[i].relatives_in_care_homes is None:
                            households_super_area[i].relatives_in_care_homes = (person,)
                        else:
                            households_super_area[i].relatives_in_care_homes = tuple(
                                (
                                    *households_super_area[i].relatives_in_care_homes,
                                    person,
                                )
                            )

    def get_possible_venues_for_person(self, person):
        if person.residence.group.relatives_in_care_homes is None:
            return
        return [relative.residence.group for relative in person.residence.group.relatives_in_care_homes if relative.dead is False]

    def get_social_venue_for_person(self, person):
        relatives = person.residence.group.relatives_in_care_homes
        if relatives is None:
            return None
        alive_relatives = [relative for relative in relatives if relative.dead is False]
        return alive_relatives[
            np.random.randint(0, len(alive_relatives))
        ].residence.group

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

        #if (
        #    person.residence.group.spec == "care_home"
        #    or person.residence.group.relatives_in_care_homes is None
        #):
        #    return 0
        ## do not visit dead people
        #if (
        #    len(
        #        [
        #            person
        #            for person in person.residence.group.relatives_in_care_homes
        #            if person.dead is False
        #        ]
        #    )
        #    == 0
        #):
        #    return 0
        if sex == "m":
            probability = self.male_probabilities[age]
        else:
            probability = self.female_probabilities[age]
        if is_weekend:
            probability = probability * self.weekend_boost
        return probability
