import numpy as np
import pandas as pd
from random import random
import datetime
from collections import Counter, defaultdict
from june import paths
from typing import List, Optional

from june.records import Record
from june.domains import Domain
from june.demography import Population
from june.geography import SuperAreas
from june.epidemiology.infection import InfectionSelector, HealthIndexGenerator
from june.epidemiology.epidemiology import Epidemiology
from june.utils import parse_age_probabilities


class InfectionSeed:
    """
    The infection seed takes a dataframe of cases to seed per capita, per age, and per region.
    There are multiple ways to construct the dataframe, from deaths, tests, etc. Each infection seed
    is associated to one infection selector, so if we run multiple infection types, there could be multiple infection
    seeds for each infection type.
    """

    def __init__(
        self,
        world: "World",
        infection_selector: InfectionSelector,
        daily_cases_per_capita_per_age_per_region: pd.DataFrame,
        seed_past_infections: bool = True,
        seed_strength=1.0,
    ):
        """
        Class that generates the seed for the infection.

        Parameters
        ----------
        world:
            world to infect
        infection_selector:
            selector to generate infections
        daily_cases_per_capita_per_region:
            Double indexed dataframe. First index: date, second index: age in brackets "0-100",
            columns: region names, use "all" as placeholder for whole England.
            Example:
                date,age,North East,London
                2020-07-01,0-100,0.05,0.1
        seed_past_infections:
            whether to seed infections that started past the initial simulation point.
        """
        self.world = world
        self.infection_selector = infection_selector
        self.daily_cases_per_capita_per_age_per_region = self._parse_input_dataframe(
            df=daily_cases_per_capita_per_age_per_region,
            seed_strength=seed_strength,
        )
        self.min_date = (
            self.daily_cases_per_capita_per_age_per_region.index.get_level_values(
                "date"
            ).min()
        )
        self.max_date = (
            self.daily_cases_per_capita_per_age_per_region.index.get_level_values(
                "date"
            ).max()
        )
        self.dates_seeded = set()
        self.past_infections_seeded = not (seed_past_infections)
        self.seed_strength = seed_strength

    def _parse_input_dataframe(self, df, seed_strength=1.0):
        """
        Parses ages by expanding the intervals.
        """
        multi_index = pd.MultiIndex.from_product(
            [df.index.get_level_values("date").unique(), range(0, 100)],
            names=["date", "age"],
        )
        ret = pd.DataFrame(index=multi_index, columns=df.columns, dtype=float)
        for date in df.index.get_level_values("date"):
            for region in df.loc[date].columns:
                cases_per_age = parse_age_probabilities(
                    df.loc[date, region].to_dict(), fill_value=0.0
                )
                ret.loc[date, region] = np.array(cases_per_age)
        ret *= seed_strength
        return ret

    @classmethod
    def from_global_age_profile(
        cls,
        world: "World",
        infection_selector: InfectionSelector,
        daily_cases_per_region: pd.DataFrame,
        seed_strength: float = 1.0,
        age_profile: Optional[dict] = None,
    ):
        """
        seed_strength:
            float that controls the strength of the seed
        age_profile:
            dictionary with weight on age groups. Example:
            age_profile = {'0-20': 0., '21-50':1, '51-100':0.}
            would only infect people aged between 21 and 50
        """
        if age_profile is None:
            age_profile = {"0-100": 1.0}
        multi_index = pd.MultiIndex.from_product(
            [daily_cases_per_region.index.values, age_profile.keys()],
            names=["date", "age"],
        )
        df = pd.DataFrame(
            index=multi_index, columns=daily_cases_per_region.columns, dtype=float
        )
        for region in daily_cases_per_region.columns:
            for age_key, age_value in age_profile.items():
                df.loc[(daily_cases_per_region.index, age_key), region] = (
                    age_value * daily_cases_per_region[region].values
                )
        return cls(
            world=world,
            infection_selector=infection_selector,
            daily_cases_per_capita_per_age_per_region=df,
            seed_strength=seed_strength,
        )

    @classmethod
    def from_uniform_cases(
        cls,
        world: "World",
        infection_selector: InfectionSelector,
        cases_per_capita: float,
        date: str,
        seed_strength=1.0,
    ):
        date = pd.to_datetime(date)
        mi = pd.MultiIndex.from_product([[date], ["0-100"]], names=["date", "age"])
        df = pd.DataFrame(index=mi, columns=["all"])
        df[:] = cases_per_capita
        return cls(
            world=world,
            infection_selector=infection_selector,
            daily_cases_per_capita_per_age_per_region=df,
            seed_strength=seed_strength,
        )

    def infect_super_area(
        self, super_area, cases_per_capita_per_age, time, record=None
    ):
        people = super_area.people
        infection_id = self.infection_selector.infection_class.infection_id()
        n_people_by_age = defaultdict(int)
        susceptible_people_by_age = defaultdict(list)
        for person in people:
            n_people_by_age[person.age] += 1
            if person.immunity.get_susceptibility(infection_id) > 0:
                susceptible_people_by_age[person.age].append(person)
        for age, susceptible in susceptible_people_by_age.items():
            # Need to rescale to number of susceptible people in the simulation.
            rescaling = n_people_by_age[age] / len(susceptible_people_by_age[age])
            for person in susceptible:
                prob = cases_per_capita_per_age.loc[age] * rescaling
                if random() < prob:
                    self.infection_selector.infect_person_at_time(person=person, time=time)
                    if record:
                        record.accumulate(
                            table_name="infections",
                            location_spec="infection_seed",
                            region_name=person.super_area.region.name,
                            location_id=0,
                            infected_ids=[person.id],
                            infector_ids=[person.id],
                            infection_ids=[person.infection.infection_id()],
                        )
                    if time < 0:
                        time_from_infection = -time
                        # Update transmission probability
                        person.infection.transmission.update_infection_probability(
                            time_from_infection=time_from_infection
                        )
                        # Need to update trajectories to current stage
                        symptoms = person.symptoms
                        while time_from_infection > symptoms.trajectory[symptoms.stage+1][0]:
                            symptoms.stage += 1
                            symptoms.tag = symptoms.trajectory[symptoms.stage][1]
                            if symptoms.stage == len(symptoms.trajectory)-1:
                                break
                        # Need to check if the person has already recovered or died
                        if "dead" in symptoms.tag.name:
                            Epidemiology.bury_the_dead(world=self.world, person=person, record=record)
                        elif "recovered" == symptoms.tag.name:
                            Epidemiology.recover(person=person, record=record)


    def infect_super_areas(
        self,
        cases_per_capita_per_age_per_region: pd.DataFrame,
        time: float,
        record: Optional[Record] = None,
    ):
        """
        Infect super areas with numer of cases given by data frame

        Parameters
        ----------
        n_cases_per_super_area:
            data frame containig the number of cases per super area
        time:
            Time where infections start (could be negative if they started before the simulation)
        """
        for super_area in self.world.super_areas:
            if "all" in cases_per_capita_per_age_per_region.columns:
                cases_per_capita_per_age = cases_per_capita_per_age_per_region["all"]
            else:
                cases_per_capita_per_age = cases_per_capita_per_age_per_region[
                    super_area.region.name
                ]
            self.infect_super_area(
                super_area=super_area,
                cases_per_capita_per_age=cases_per_capita_per_age,
                time=time,
                record=record,
            )

    def unleash_virus_per_day(
        self,
        date: datetime,
        time: float = 0,
        record: Optional[Record] = None,
        seed_past_infections=True,
    ):
        """
        Infect super areas at a given ```date```

        Parameters
        ----------
        date:
            current date
        time:
            time since start of the simulation
        record:
            Record object to record infections
        seed_past_infections:
            whether to seed infections that started past the initial simulation point.
        """
        if not self.past_infections_seeded:
            self._seed_past_infections(date=date, time=time, record=record)
            self.past_infections_seeded = True
        is_seeding_date = self.max_date >= date >= self.min_date
        date_str = date.date().strftime("%Y-%m-%d")
        not_yet_seeded_date = (
            date_str not in self.dates_seeded
            and date_str
            in self.daily_cases_per_capita_per_age_per_region.index.get_level_values(
                "date"
            )
        )
        if is_seeding_date and not_yet_seeded_date:
            self.infect_super_areas(
                cases_per_capita_per_age_per_region=self.daily_cases_per_capita_per_age_per_region.loc[
                    date
                ],
                time=time,
                record=record,
            )
            self.dates_seeded.add(date_str)

    def _seed_past_infections(self, date, time, record):
        past_dates = []
        for (
            past_date
        ) in self.daily_cases_per_capita_per_age_per_region.index.get_level_values(
            "date"
        ).unique():
            if past_date.date() < date.date():
                past_dates.append(past_date)
        for past_date in past_dates:
            past_time = (past_date.date() - date.date()).days
            past_date_str = past_date.date().strftime("%Y-%m-%d")
            self.dates_seeded.add(past_date_str)
            self.infect_super_areas(
                cases_per_capita_per_age_per_region=self.daily_cases_per_capita_per_age_per_region.loc[
                    past_date
                ],
                time=past_time,
                record=record,
            )
            if record:
                # record past infections and deaths.
                record.time_step(timestamp=past_date)

class InfectionSeeds:
    """
    Groups infection seeds and applies them sequentially.
    """

    def __init__(self, infection_seeds: List[InfectionSeed], seed_past_infections=True):
        self.infection_seeds = infection_seeds
        self.seed_past_infections = seed_past_infections

    def unleash_virus_per_day(
        self, date: datetime, time: float = 0, record: Optional[Record] = None
    ):
        for seed in self.infection_seeds:
            seed.unleash_virus_per_day(
                date=date,
                record=record,
                time=time,
                seed_past_infections=self.seed_past_infections,
            )

    def __iter__(self):
        return iter(self.infection_seeds)

    def __getitem__(self, item):
        return self.infection_seeds[item]
