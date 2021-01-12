import numpy as np
import pandas as pd
from random import shuffle
import datetime
from collections import Counter, defaultdict
from june import paths
from typing import List, Optional

from june.records import Record
from june.domain import Domain
from june.demography import Population
from june.geography import SuperAreas
from june.infection.infection_selector import InfectionSelector
from june.infection.health_index.health_index import HealthIndexGenerator

default_infection_seeds_config_file = (
    paths.configs_path / "default/infection/infection_seeds.yaml"
)


class InfectionSeed:
    def __init__(
        self,
        world: "World",
        infection_selector: InfectionSelector,
        seed_strength: float = 1.0,
        age_profile: Optional[dict] = None,
        daily_super_area_cases: Optional[pd.DataFrame] = None,
    ):
        """
        Class that generates the seed for the infection.

        Parameters
        ----------
        world:
            world to infect
        infection_selector:
            selector to generate infections
        seed_strength:
            float that controls the strength of the seed
        age_profile:
            dictionary with weight on age groups. Example:
            age_profile = {'0-20': 0., '21-50':1, '51-100':0.}
            would only infect people aged between 21 and 50
        """
        self.world = world
        self.infection_selector = infection_selector
        self.seed_strength = seed_strength
        self.age_profile = age_profile
        self.daily_super_area_cases = daily_super_area_cases
        if self.daily_super_area_cases is not None:
            self.min_date = self.daily_super_area_cases.index.min()
            self.max_date = self.daily_super_area_cases.index.max()
        self.dates_seeded = set()

    def unleash_virus(
        self,
        population: "Population",
        n_cases: int,
        time: float,
        mpi_rank: int = 0,
        mpi_comm: Optional["MPI.COMM_WORLD"] = None,
        mpi_size: Optional[int] = None,
        box_mode=False,
        record: Optional["Record"] = None,
    ):
        """
        Infects ```n_cases``` people in ```population```

        Parameters
        ----------
        population:
            population to infect
        n_cases:
            number of initial cases
        mpi_rank:
            rank of the process
        mpi_comm:
            mpi comm_world to enable communication between
            different processes
        mpi_size:
            number of processes
        box_mode:
            whether to run on box mode
        """
        if mpi_rank == 0:
            susceptible_ids = [
                person.id for person in population.people if person.susceptible
            ]
            n_cases = round(self.seed_strength * n_cases)
            if self.age_profile is None:
                ids_to_infect = np.random.choice(
                    susceptible_ids,
                    n_cases,
                    replace=False,
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
                    self.infection_selector.infect_person_at_time(person, time=time)
                    if record is not None:
                        record.accumulate(
                            table_name="infections",
                            location_spec="infection_seed",
                            region_name=person.super_area.region.name,
                            location_id=0,
                            infected_ids=[person.id],
                            infector_ids=[person.id],
                            infection_ids=[person.infection.infection_id()],
                        )
        else:
            for inf_id in ids_to_infect:
                # if isinstance(self.world, Domain):
                if box_mode:
                    person_to_infect = self.world.members[0].people[inf_id]
                else:
                    person_to_infect = self.world.people.get_from_id(inf_id)
                self.infection_selector.infect_person_at_time(
                    person_to_infect, time=time
                )
                if record is not None:
                    record.accumulate(
                        table_name="infections",
                        location_spec="infection_seed",
                        region_name=person_to_infect.super_area.region.name,
                        location_id=0,
                        infected_ids=[person_to_infect.id],
                        infector_ids=[person_to_infect.id],
                        infection_ids=[person_to_infect.infection.infection_id()],
                    )

    def select_susceptiles_by_age(
        self, susceptible_ids: List[int], n_cases: int
    ) -> List[int]:
        """
        Select cases according to an age profile

        Parameters
        ----------
        susceptible_ids:
            list of ids of susceptible people to select from
        n_cases:
            number of cases

        Returns
        -------
        choices:
            ids of people to infect, following the age profile given
        """
        n_per_age_group = n_cases * np.array(list(self.age_profile.values()))
        shuffle(susceptible_ids)
        choices = []
        for idx, age_group in enumerate(self.age_profile.keys()):
            age_choices = self.get_people_from_age_group(
                susceptible_ids, int(round(n_per_age_group[idx])), age_group
            )
            choices.extend(age_choices)
        return choices

    def get_people_from_age_group(
        self, susceptible_ids: List[int], n_people: int, age_group: str
    ) -> List[int]:
        """
        Get ```n_people``` in a given ```age_group``` from the list of susceptible_ids

        Parameters
        ----------
        susceptible_ids:
            list of ids of susceptible people to select from
        n_people:
            number of people to select
        age_group:
            age limits to select from (Example: '18-25')

        Returns
        -------
        ids of people in age group
        """
        choices = []
        for person_id in susceptible_ids:
            if len(choices) == n_people:
                break
            if (
                int(age_group.split("-")[0])
                <= self.world.people.get_from_id(person_id).age
                < int(age_group.split("-")[1])
            ):
                choices.append(person_id)
        return choices

    def infect_super_areas(
        self,
        n_cases_per_super_area: pd.DataFrame,
        time: float = 0,
        record: Optional[Record] = None,
    ):
        """
        Infect super areas with numer of cases given by data frame

        Parameters
        ----------
        n_cases_per_super_area:
            data frame containig the number of cases per super area
        """
        for super_area in self.world.super_areas:
            try:
                n_cases = int(n_cases_per_super_area[super_area.name])
                self.unleash_virus(
                    Population(super_area.people),
                    n_cases=n_cases,
                    record=record,
                    time=time,
                )
            except KeyError as e:
                raise KeyError("There is no data on cases for super area: %s" % str(e))

    def unleash_virus_per_day(
        self, date: datetime, time: float = 0, record: Optional[Record] = None
    ):
        """
        Infect super areas at a given ```date```

        Parameters
        ----------
        date:
            datetime object
        """
        is_seeding_date = self.max_date >= date >= self.min_date
        date_str = date.date().strftime("%Y-%m-%d")
        not_yet_seeded_date = (
            date_str not in self.dates_seeded
            and date_str in self.daily_super_area_cases.index
        )
        if is_seeding_date and not_yet_seeded_date:
            self.infect_super_areas(
                n_cases_per_super_area=self.daily_super_area_cases.loc[date_str],
                time=time,
                record=record,
            )
            self.dates_seeded.add(date_str)


class InfectionSeeds:
    """
    Groups infection seeds and applies them sequentially.
    """

    def __init__(self, infection_seeds: List[InfectionSeed]):
        self.infection_seeds = infection_seeds

    def unleash_virus_per_day(
        self, date: datetime, time: float = 0, record: Optional[Record] = None
    ):
        for seed in self.infection_seeds:
            seed.unleash_virus_per_day(date=date, record=record, time=time)

    def __iter__(self):
        return iter(self.infection_seeds)
