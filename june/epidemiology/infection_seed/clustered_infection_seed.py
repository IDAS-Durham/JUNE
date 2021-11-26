import pandas as pd
import numpy as np
from random import shuffle, random
from collections import defaultdict

from .infection_seed import InfectionSeed
from june.epidemiology.infection import InfectionSelector


class ClusteredInfectionSeed(InfectionSeed):
    def __init__(
        self,
        world: "World",
        infection_selector: InfectionSelector,
        daily_cases_per_capita_per_age_per_region: pd.DataFrame,
        seed_past_infections: bool = True,
        seed_strength=1.0,
        probability_infected_housemate=0.5,
    ):
        super().__init__(
            world=world,
            infection_selector=infection_selector,
            daily_cases_per_capita_per_age_per_region=daily_cases_per_capita_per_age_per_region,
            seed_past_infections=seed_past_infections,
            seed_strength=seed_strength,
        )
        self.probability_infected_housemate = probability_infected_housemate

    def get_people_to_infect_in_super_area_by_age(
        self,
        super_area,
        cases_per_capita_per_age,
        susceptible_people_by_age,
        n_people_by_age,
    ):
        ret = {}
        for age in cases_per_capita_per_age.index:
            n_susceptible = len(susceptible_people_by_age[age])
            if n_susceptible == 0:
                ret[age] = 0
                continue
            rescaling = n_people_by_age[age] / len(susceptible_people_by_age[age])
            expected_infected = n_susceptible * cases_per_capita_per_age.loc[age]
            ret[age] = int(expected_infected)
            reminder = expected_infected - ret[age]
            ret[age] += int(random() < reminder)
        return ret

    def can_person_be_infected(self, age_distribution, person, infection_id, error):
        if person.immunity.get_susceptibility(infection_id) == 0:
            return False
        return random() < sum(
            age_distribution.loc[person.age - error : person.age + error]
        )

    def get_total_people_to_infect(self, people, cases_per_capita_per_age):
        people_by_age = defaultdict(int)
        for person in people:
            people_by_age[person.age] += 1
        total = sum(
            [
                people_by_age[age] * cases_per_capita_per_age.loc[age]
                for age in people_by_age
            ]
        )
        ret = int(total)
        ret += int(random() < (total - ret))
        return ret

    def _infect_super_area(
        self, super_area, cases_per_capita_per_age, time, record=None
    ):

        infection_id = self.infection_selector.infection_class.infection_id()
        people = super_area.people
        total_to_infect = self.get_total_people_to_infect(
            people=people, cases_per_capita_per_age=cases_per_capita_per_age
        )
        age_distribution = cases_per_capita_per_age / cases_per_capita_per_age.sum()
        people_indices = np.arange(0, len(people))
        np.random.shuffle(people_indices)
        while total_to_infect > 0:
            for idx in people_indices:
                person = people[idx]
                if self.can_person_be_infected(
                    age_distribution=age_distribution,
                    person=person,
                    infection_id=infection_id,
                    error=0,
                ):
                    self.infect_person(person=person, time=time, record=record)
                    if time < 0:
                        self.bring_infection_up_to_date(
                            person=person, time_from_infection=-time, record=record
                        )
                    total_to_infect -= 1
                    if total_to_infect < 1:
                        return
                    residence = person.residence.group
                    if residence.type == "communal" or residence.spec == "care_home":
                        continue
                    for resident in residence.residents:
                        if resident == person:
                            continue
                        if self.can_person_be_infected(
                            age_distribution=age_distribution,
                            person=resident,
                            infection_id=infection_id,
                            error = 2
                        ):
                            self.infect_person(
                                person=resident, time=time, record=record
                            )
                            if time < 0:
                                self.bring_infection_up_to_date(
                                    person=resident,
                                    time_from_infection=-time,
                                    record=record,
                                )
                            total_to_infect -= 1
                            if total_to_infect < 1:
                                return

    def get_household_score(self, household, age_distribution):
        if len(household.residents) == 0:
            return 0
        ret = 0
        for resident in household.residents:
            ret += age_distribution.loc[resident.age]
        #return ret
        return ret / np.sqrt(len(household.residents))

    def infect_super_area(
        self, super_area, cases_per_capita_per_age, time, record=None
    ):

        infection_id = self.infection_selector.infection_class.infection_id()
        people = super_area.people
        total_to_infect = self.get_total_people_to_infect(
            people=people, cases_per_capita_per_age=cases_per_capita_per_age
        )
        age_distribution = cases_per_capita_per_age / cases_per_capita_per_age.sum()
        households = np.array(super_area.households)
        scores = [self.get_household_score(h, age_distribution) for h in households]
        cum_scores = np.cumsum(scores)
        while total_to_infect > 0:
            num = random() * cum_scores[-1]
            idx = np.searchsorted(cum_scores, num)
            household = households[idx]
            for person in household.people:
                if person.immunity.get_susceptibility(infection_id) > 0:
                    self.infect_person(
                        person=person, time=time, record=record
                    )
                    if time < 0:
                        self.bring_infection_up_to_date(
                            person=person,
                            time_from_infection=-time,
                            record=record,
                        )
                    total_to_infect -= 1
                    if total_to_infect < 1:
                        return




    #    age_distribution = cases_per_capita_per_age / cases_per_capita_per_age.sum()
