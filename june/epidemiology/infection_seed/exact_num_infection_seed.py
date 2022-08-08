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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from june.world import World

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

        Parameters
        ----------
        n_cases_per_super_area:
            data frame containig the number of cases per super area
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
            col_name_split = cases_per_capita_per_age_per_region.columns[0].split("-")
            if len(col_name_split) == 2:
                # region
                iter_type = self.world.regions
            else:
                if len(col_name_split[-1]) == 1:
                    # superarea
                    iter_type = self.world.super_areas
                else:
                    # area
                    iter_type = self.world.areas

            num_locations_to_seed = len(cases_per_capita_per_age_per_region.columns)
            for this_area in iter_type:
                try:
                    cases_per_capita_per_age = cases_per_capita_per_age_per_region[
                        this_area.name
                    ]
                except:
                    continue

                if self._need_to_seed_accounting_secondary_infections(date=date):
                    cases_per_capita_per_age = (
                        self._adjust_seed_accounting_secondary_infections(
                            cases_per_capita_per_age=cases_per_capita_per_age,
                            region=this_area,
                            date=date,
                            time=time,
                        )
                    )

                self.infect_super_area(
                    super_area=this_area,
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
        infection_id = self.infection_selector.infection_class.infection_id()

        total_to_infect = cases_per_capita_per_age.sum()
        households = []
        area_type = type(super_area).__name__
        if area_type == "CampWorld":
            for r in super_area.regions:
                for sa in r.super_areas:
                    for area in sa.areas:
                        households += area.households
        elif area_type == "Region":
            for sa in super_area.super_areas:
                for area in sa.areas:
                    households += area.households
        elif area_type == "SuperArea":
            for area in super_area.areas:
                households += area.households
        elif area_type == "CampArea":
            households += super_area.households
        else:
            raise TypeError("invalid seeding location type: " + area_type)

        age_distribution = cases_per_capita_per_age / cases_per_capita_per_age.sum()
        scores = [self.get_household_score(h, age_distribution) for h in households]

        cum_scores = np.cumsum(scores)
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
