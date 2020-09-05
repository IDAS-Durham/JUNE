import numpy as np
import pandas as pd
from random import shuffle
import datetime
from collections import Counter
from june import paths
from typing import List, Optional
from june.demography import Population
from june.demography.geography import SuperAreas
from june.infection.infection_selector import InfectionSelector
from june.infection.health_index import HealthIndexGenerator

default_n_cases_region_filename = paths.data_path / "input/seed/n_cases_region.csv"
default_msoa_region_filename = (
    paths.data_path / "input/geography/area_super_area_region.csv"
)


class InfectionSeed:
    def __init__(
        self,
        world: "World",
        infection_selector: InfectionSelector,
        seed_strength: float = 1.0,
        age_profile: Optional[dict] = None,
    ):
        self.world = world
        self.infection_selector = infection_selector
        self.seed_strength = seed_strength
        self.age_profile = age_profile
        self.dates_seeded = []

    def unleash_virus(
        self,
        population: "Population",
        n_cases: int,
        mpi_rank: int = 0,
        mpi_comm: Optional["MPI.COMM_WORLD"] = None,
        mpi_size: Optional[int] = None,
    ):
        if mpi_rank == 0:
            susceptible_ids = [
                person.id for person in population.people if person.susceptible
            ]
            n_cases = round(self.seed_strength * n_cases)
            if self.age_profile is None:
                ids_to_infect = np.random.choice(
                    susceptible_ids, n_cases, replace=False,
                )
            else:
                ids_to_infect = self.select_susceptiles_by_age(susceptible_ids, n_cases)
        if mpi_comm is not None:
            for rank_receiving in range(1, mpi_size):
                mpi_comm.send(ids_to_infect, est=rank_receiving, tag=0)
            if mpi_rank > 0:
                ids_to_infect = mpi_comm.recv(source=0, tag=0)
            for inf_id in ids_to_infect:
                if inf_id in self.world.people.people_dict:
                    person = self.world.people.get_from_id(inf_id)
                    self.infection_selector.infect_person_at_time(person, 0.0)
        else:
            for inf_id in ids_to_infect:
                self.infection_selector.infect_person_at_time(
                    self.world.people[inf_id], 0.0
                )

    def select_susceptiles_by_age(self, susceptible_ids: List[int], n_cases: int):
        n_per_age_group = n_cases * np.array(list(self.age_profile.values()))
        shuffle(susceptible_ids)
        choices = []
        for idx, age_group in enumerate(self.age_profile.keys()):
            print(age_group)
            age_choices = self.get_people_from_age_group(
                susceptible_ids, int(round(n_per_age_group[idx])), age_group
            )
            print('age choices= ',age_choices)
            choices.extend(age_choices)
        return choices

    def get_people_from_age_group(self, susceptible_ids: List[int], n_people: int, age_group: str):
        choices = []
        for idx, person_id in enumerate(susceptible_ids):
            if len(choices) == n_people:
                break
            if (
                int(age_group.split("-")[0])
                <= self.world.people[person_id].age
                < int(age_group.split("-")[1])
            ):
                choices.append(person_id)
        return choices

    def infect_super_areas(self, n_daily_cases_by_super_area: pd.DataFrame):
        for super_area in self.world.super_areas:
            try:
                n_cases = int(n_daily_cases_by_super_area[super_area.name])
                self.unleash_virus(
                    Population(super_area.people), n_cases=n_cases,
                )
            except KeyError as e:
                raise KeyError("There is no data on cases for super area: %s" % str(e))

    def unleash_virus_per_day(
        self, n_cases_by_super_area: pd.DataFrame, date: "datetime",
    ):
        date_str = date.strftime("%Y-%m-%d")
        date = date.date()
        if date not in self.dates_seeded and date in n_cases_by_super_area.index:
            self.infect_super_areas(n_cases_by_super_area.loc[date_str])
            self.dates_seeded.append(date)

