from typing import Union, Dict
import datetime
from random import sample, choices

from .event import Event

class IncidenceSetter(Event):
    """
    This Event is used to set a specific incidence per region at some point in the code.
    It can be used to correct, based on data, the current epidemiological state of the code.
    The added infection types are sampled from the currrent ones.
    """

    def __init__(
        self,
        start_time: Union[str, datetime.datetime],
        end_time: Union[str, datetime.datetime],
        incidence_per_region: Dict[str, float],
    ):
        super().__init__(start_time=start_time, end_time=end_time)
        self.incidence_per_region = incidence_per_region

    def initialise(self, world):
        pass

    def apply(self, world, simulator, activities=None, day_type=None):
        selectors = simulator.epidemiology.infection_selectors
        for region in world.regions:
            if region.name in self.incidence_per_region:
                target_incidence = self.incidence_per_region[region.name]
                people = region.people
                infected_people = [person for person in people if person.infected]
                incidence = len(infected_people) / len(people)
                if incidence > target_incidence:
                    n_to_remove = int((incidence - target_incidence) * len(people))
                    to_cure = sample(infected_people, n_to_remove)
                    for person in to_cure:
                        person.infection = None
                elif incidence < target_incidence:
                    n_to_add = int((target_incidence - incidence) * len(people))
                    to_infect = sample(people, k=2 * n_to_add)
                    infected = choices(infected_people, k=2 * n_to_add)
                    counter = 0
                    for person, infected_ref in zip(to_infect, infected):
                        if person.infected:
                            continue
                        counter += 1
                        selectors.infect_person_at_time(
                            person,
                            simulator.timer.now,
                            infected_ref.infection.infection_id(),
                        )
                        if counter == n_to_add:
                            break
