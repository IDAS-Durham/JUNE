import numpy as np
import pandas as pd
import random
import datetime
import logging
from collections import defaultdict
from typing import List, Optional

from june.records import Record
from june.epidemiology.infection import InfectionSelector

from .infection_seed import InfectionSeed
from june.epidemiology.infection import InfectionSelector

from june.world import World
from june.geography import Region, Area, SuperArea

seed_logger = logging.getLogger("seed")


class ExactNumInfectionSeed(InfectionSeed):
    def __init__(
        self,
        world: "World",
        infection_selector: InfectionSelector,
        daily_cases_per_capita_per_age_per_region: pd.DataFrame,
        seed_past_infections: bool = True,
        seed_strength=1.0,
        # account_secondary_infections=False,
    ):
        super().__init__(
            world=world,
            infection_selector=infection_selector,
            daily_cases_per_capita_per_age_per_region=daily_cases_per_capita_per_age_per_region,
            seed_past_infections=seed_past_infections,
            seed_strength=seed_strength,
            account_secondary_infections=False,
        )
        # use age bin in exact number mode. No need to expanding individual ages.
        self.daily_cases_per_capita_per_age_per_region = (
            daily_cases_per_capita_per_age_per_region * seed_strength
        )

        self.iter_type_set = set()
        if "all" not in daily_cases_per_capita_per_age_per_region.columns:
            # generate list of existing regions, superareas, areas
            regions = [region.name for region in self.world.regions]
            super_areas = [super_area.name for super_area in self.world.super_areas]
            areas = [area.name for area in self.world.areas]

            # check if seeding locations are existing in curent world
            for loc_name in self.daily_cases_per_capita_per_age_per_region.columns:
                if loc_name in regions:
                    self.iter_type_set.add(self.world.regions)
                elif loc_name in super_areas:
                    self.iter_type_set.add(self.world.super_areas)
                elif loc_name in areas:
                    self.iter_type_set.add(self.world.areas)
                else:
                    raise TypeError(
                        "invalid seeding location (column) name: " + loc_name
                    )

    def infect_super_area(
        self, super_area, cases_per_capita_per_age, time, record=None
    ):
        people = super_area.people
        infection_id = self.infection_selector.infection_class.infection_id()

        age_ranges = []
        for age in cases_per_capita_per_age.index:
            agemin, agemax = age.split("-")
            age_ranges.append([int(agemin), int(agemax)])

        N_seeded = np.zeros(len(age_ranges), dtype="int")
        random.seed()
        for person in random.sample(list(people), len(people)):
            in_seed_age_range = False
            for j in range(len(age_ranges)):
                if (
                    person.age >= age_ranges[j][0]
                    and person.age < age_ranges[j][1]
                    and N_seeded[j] < cases_per_capita_per_age[j]
                ):
                    in_seed_age_range = True
                    break
            if (
                in_seed_age_range
                and person.immunity.get_susceptibility(infection_id) > 0
            ):
                self.infect_person(person=person, time=time, record=record)
                self.current_seeded_cases[person.region.name] += 1
                if time < 0:
                    self.bring_infection_up_to_date(
                        person=person, time_from_infection=-time, record=record
                    )

                N_seeded[j] += 1
                if np.all(N_seeded == np.array(cases_per_capita_per_age)):
                    break

    def infect_super_areas(
        self,
        cases_per_capita_per_age_per_region: pd.DataFrame,
        time: float,
        date: datetime.datetime,
        record: Optional[Record] = None,
    ):
        """
        Infect world/region/super_area/area with number of cases given by data frame
        Not only super area, but still keep the old function name for now.

        Parameters
        ----------
        n_cases_per_super_area:
            data frame containig the number of cases per world/region/super_area/area
        time:
            Time where infections start (could be negative if they started before the simulation)
        """
        if "all" in cases_per_capita_per_age_per_region.columns:
            self.infect_super_area(
                super_area=self.world,
                cases_per_capita_per_age=cases_per_capita_per_age_per_region["all"],
                time=time,
                record=record,
            )
        else:
            num_locations_to_seed = len(cases_per_capita_per_age_per_region.columns)
            for geo_type in self.iter_type_set:
                for this_loc in geo_type:
                    try:
                        cases_per_capita_per_age = cases_per_capita_per_age_per_region[
                            this_loc.name
                        ]
                    except KeyError:
                        continue

                    """ 
                    ### 
                    # TO DO: rewite self._adjust_seed_accounting_secondary_infections to work for superarea/area
                    ###
                    if self._need_to_seed_accounting_secondary_infections(date=date):
                        cases_per_capita_per_age = (
                            self._adjust_seed_accounting_secondary_infections(
                                cases_per_capita_per_age=cases_per_capita_per_age,
                                region=this_loc,
                                date=date,
                                time=time,
                            )
                        )
                    """
                    self.infect_super_area(
                        super_area=this_loc,
                        cases_per_capita_per_age=cases_per_capita_per_age,
                        time=time,
                        record=record,
                    )
                    num_locations_to_seed -= 1

            # check if all columns are seeded
            assert (
                num_locations_to_seed < 1
            ), "something wrong in location (column) name !!!"


class ExactNumClusteredInfectionSeed(ExactNumInfectionSeed):
    def __init__(
        self,
        world: "World",
        infection_selector: InfectionSelector,
        daily_cases_per_capita_per_age_per_region: pd.DataFrame,
        seed_past_infections: bool = True,
        seed_strength=1.0,
        # account_secondary_infections=False,
    ):
        super().__init__(
            world=world,
            infection_selector=infection_selector,
            daily_cases_per_capita_per_age_per_region=daily_cases_per_capita_per_age_per_region,
            seed_past_infections=seed_past_infections,
            seed_strength=seed_strength,
            # account_secondary_infections=account_secondary_infections,
        )

    def get_household_score(self, household, age_distribution):
        if len(household.residents) == 0:
            return 0
        age_ranges = []
        for age in age_distribution.index:
            agemin, agemax = age.split("-")
            age_ranges.append([int(agemin), int(agemax)])
        ret = 0
        for resident in household.residents:
            for ii, age_bin in enumerate(age_ranges):
                if resident.age >= age_bin[0] and resident.age < age_bin[1]:
                    ret += age_distribution[ii]
                    break
        return ret / np.sqrt(len(household.residents))

    def infect_super_area(
        self, super_area, cases_per_capita_per_age, time, record=None
    ):
        households = []
        if isinstance(super_area, World):
            for r in super_area.regions:
                for sa in r.super_areas:
                    for area in sa.areas:
                        households += area.households
        elif isinstance(super_area, Region):
            for sa in super_area.super_areas:
                for area in sa.areas:
                    households += area.households
        elif isinstance(super_area, SuperArea):
            for area in super_area.areas:
                households += area.households
        elif isinstance(super_area, Area):
            households += super_area.households
        else:
            raise TypeError(
                "invalid seeding location type: " + type(super_area).__name__
            )

        age_distribution = cases_per_capita_per_age / cases_per_capita_per_age.sum()
        scores = [self.get_household_score(h, age_distribution) for h in households]
        cum_scores = np.cumsum(scores)

        infection_id = self.infection_selector.infection_class.infection_id()
        total_to_infect = cases_per_capita_per_age.sum()

        seeded_households = set()
        while total_to_infect > 0:
            num = random.random() * cum_scores[-1]
            idx = np.searchsorted(cum_scores, num)
            household = households[idx]
            if household.id in seeded_households:
                continue
            for person in household.residents:
                if person.immunity.get_susceptibility(infection_id) > 0:
                    self.infect_person(person=person, time=time, record=record)
                    if time < 0:
                        self.bring_infection_up_to_date(
                            person=person,
                            time_from_infection=-time,
                            record=record,
                        )
                    total_to_infect -= 1
                    if total_to_infect < 1:
                        return
                    seeded_households.add(household.id)
