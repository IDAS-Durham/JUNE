from typing import Dict, Union
from random import random, shuffle, randint
import logging
import datetime

from .event import Event
from june.utils import parse_age_probabilities

logger = logging.getLogger("domestic_care")


class DomesticCare(Event):
    """
    This event models people taking care of their elderly who live
    alone or in couples. The logic is that at the beginning of each
    leisure time-step, people who have caring responsibilites go
    to their relatives household for the duration of their time-step.

    Parameters
    ----------
    start_time
        time from when the event is active (default is always)
    end_time
        time when the event ends (default is always)
    needs_care_probabilities
        dictionary mapping the probability of needing care per age.
        Example:
        needs_care_probabilities = {"0-65" : 0.0, "65-100" : 0.5}
    relative_frequency
        relative factor to scale the overall probabilities in needs_care_probabilities
        useful for when we want to change the caring frequency with lockdowns, etc.
    """

    def __init__(
        self,
        start_time: Union[str, datetime.datetime],
        end_time: Union[str, datetime.datetime],
        needs_care_probabilities: Dict[str, float],
        daily_going_probability=1.0,
    ):
        super().__init__(start_time=start_time, end_time=end_time)
        self.needs_care_probabilities = parse_age_probabilities(
            needs_care_probabilities
        )
        self.daily_going_probability = daily_going_probability

    def initialise(self, world):
        self._link_carers_to_households(world=world)

    def apply(self, world, activities, day_type, simulator=None):
        """
        When a household is reponsible for caring of another housheold,
        a random person is sent during leisure to take care of that household.
        We checked that the person is not at hospital when we send them.
        """
        if (
            "leisure" not in activities
            or day_type == "weekend"
            or "primary_activity" in activities
        ):
            return
        for household in world.households:
            if household.household_to_care is not None:
                household_to_care = household.household_to_care
                carers = list(household.residents)
                shuffle(carers)
                receives_care = False
                for person in carers:
                    if person.age > 18 and person.available:
                        household_to_care.add(person, activity="leisure")
                        receives_care = True
                        break
                if receives_care:
                    household_to_care.receiving_care = True
                    # make residents stay at home
                    for person in household_to_care.residents:
                        if person.available:
                            person.residence.append(person)

    def _link_carers_to_households(self, world):
        """
        Links old people households to other households that provide them with care aid.
        All linking is restricted to the super area level.
        """
        total_need_care = 0
        for super_area in world.super_areas:
            # get households that need care
            need_care = []
            can_provide_care = []
            for area in super_area.areas:
                for household in area.households:
                    if self._check_household_needs_care(household):
                        need_care.append(household)
                    if self._check_household_can_provide_care(household):
                        can_provide_care.append(household)
            shuffle(need_care)
            shuffle(can_provide_care)
            if len(need_care) > len(can_provide_care):
                logger.warning(
                    f"super area {super_area.id} does not" f"have enough carers"
                )
            for needer, provider in zip(need_care, can_provide_care):
                total_need_care += 1
                provider.household_to_care = needer

    def _check_household_needs_care(self, household):
        """
        Check if a household needs care. We take the oldest
        person in the household to be representative of the risk
        for needing care.
        """
        if household.type == "old":
            for person in household.residents:
                care_probability = self.needs_care_probabilities[person.age]
                if random() < care_probability:
                    return True
        return False

    def _check_household_can_provide_care(self, household):
        """
        We limit care providers to non-student households.
        """
        if household.type in ["student", "old"]:
            return False
        return True
