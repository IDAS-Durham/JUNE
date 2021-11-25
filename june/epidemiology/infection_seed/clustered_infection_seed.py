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
        self, super_area, cases_per_capita_per_age
    ):
        people_in_super_area = super_area.people
        people_by_age = defaultdict(int)
        for person in people_in_super_area:
            people_by_age[person.age] += 1
        ret = {}
        for age in cases_per_capita_per_age.index:
            ret[age] = people_by_age[age] * cases_per_capita_per_age.loc[age].values[0]
        return ret

    def can_person_be_infected(self, to_infect_by_age, person, infection_id):
        if person.immunity.get_susceptibility(infection_id) == 0:
            return False
        return to_infect_by_age[person.age] >= 1

    def infect_super_area(
        self, super_area, cases_per_capita_per_age, time, record=None
    ):

        infection_id = self.infection_selector.infection_class.infection_id()
        people_to_infect_by_age = self.get_people_to_infect_in_super_area_by_age(
            super_area=super_area, cases_per_capita_per_age=cases_per_capita_per_age
        )
        people_indices = np.arange(0, len(super_area.people))
        shuffle(people_indices)
        for idx in people_indices:
            person = super_area.people[idx]
            if self.can_person_be_infected(
                to_infect_by_age=people_to_infect_by_age,
                person=person,
                infection_id=infection_id,
            ):
                self.infect_person(person=person, time=time, record=record)
                if time < 0:
                    self.bring_infection_up_to_date(
                        person=person, time_from_infection=-time, record=record
                    )
                people_to_infect_by_age[person.age] -= 1
                residence = person.residence.group
                if residence.type == "communal" or residence.spec == "care_home":
                    continue
                for resident in residence.residents:
                    if resident == person:
                        continue
                    if self.can_person_be_infected(
                        to_infect_by_age=people_to_infect_by_age,
                        person=resident,
                        infection_id=infection_id,
                    ):
                        if random() < self.probability_infected_housemate:
                            self.infect_person(
                                person=resident, time=time, record=record
                            )
                            if time < 0:
                                self.bring_infection_up_to_date(
                                    person=resident,
                                    time_from_infection=-time,
                                    record=record,
                                )
                            people_to_infect_by_age[resident.age] -= 1

        if sum(people_to_infect_by_age.values()) > 0:
            susceptible_people_by_age = defaultdict(list)
            for person in super_area.people:
                if person.immunity.get_susceptibility(infection_id) > 0:
                    susceptible_people_by_age[person.age].append(person)
            for age in people_to_infect_by_age:
                n_to_infect = int(np.round(people_to_infect_by_age[age]))
                for i in range(n_to_infect):
                    if not susceptible_people_by_age[age]:
                        break
                    person = susceptible_people_by_age[age].pop()
                    self.infect_person(
                        person=person, time=time, record=record
                    )
                    if time < 0:
                        self.bring_infection_up_to_date(
                            person=person,
                            time_from_infection=-time,
                            record=record,
                        )

