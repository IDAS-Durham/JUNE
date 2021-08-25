import datetime
from typing import Union, Dict
from random import random

from june.epidemiology.infection import B117
from .event import Event


class Mutation(Event):
    """
    This events aims to reproduce a mutation effect.
    It was originally implemented to model the new Covid19 variant
    detected in the UK around November 2020. The idea is that a percentage
    of the active infections (which can vary region to region) is converted
    to the new variant, with different epidemiological charactersitics.
    Note: currently we only change the infection transmission charactersitics,
    but leaving the symptoms trajectory intact.

    Parameters
    ----------
    start_time
        time from when the event is active (default is always)
    end_time
        time when the event ends (default is always)
    regional_probabilities
        fraction of current infections that will be transformed to the new variant
    mutation_id
        unique id of the new mutation. These are generated with an adler32 encoding on
        the name.
        Covid19: 170852960
        B117: 37224668
    """

    def __init__(
        self,
        start_time: Union[str, datetime.datetime],
        end_time: Union[str, datetime.datetime],
        regional_probabilities: Dict[str, float],
        mutation_id=B117.infection_id(),
    ):
        super().__init__(start_time=start_time, end_time=end_time)
        self.regional_probabilities = regional_probabilities
        self.mutation_id = mutation_id

    def initialise(self, world=None):
        pass

    def apply(self, world, simulator, activities=None, day_type=None):
        selector = simulator.epidemiology.infection_selectors.infection_id_to_selector[
            self.mutation_id
        ]
        for person in world.people:
            if person.infected:
                probability = self.regional_probabilities.get(person.region.name, 0)
                if random() < probability:
                    new_infection = selector._make_infection(
                        person, time=person.infection.start_time
                    )
                    new_infection.time_of_testing = person.infection.time_of_testing
                    new_infection.start_time = person.infection.start_time
                    new_infection.symptoms = person.infection.symptoms
                    person.infection = new_infection
