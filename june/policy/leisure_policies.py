import datetime
import numpy as np
from collections import defaultdict
from typing import Dict, Union

from .policy import Policy, Policies, PolicyCollection
from june.exc import PolicyError
from june.utils.parse_probabilities import parse_age_probabilities
from june.groups.leisure import Leisure


class LeisurePolicy(Policy):
    def __init__(
        self,
        start_time: Union[str, datetime.datetime],
        end_time: Union[str, datetime.datetime],
    ):
        super().__init__(start_time, end_time)
        self.policy_type = "leisure"

class LeisurePolicies(PolicyCollection):
    policy_type = "leisure"
    def apply(self, date: datetime, leisure: Leisure):
        for policy in self.policies:
            policy.apply(date=date, leisure=leisure)

class CloseLeisureVenue(LeisurePolicy):
    def __init__(
        self,
        start_time: Union[str, datetime.datetime],
        end_time: Union[str, datetime.datetime],
        venues_to_close=("cinemas", "groceries"),
    ):
        """
        Template for policies that will close types of leisure venues

        Parameters
        ----------
        start_time:
            date at which to start applying the policy
        end_time:
            date from which the policy won't apply
        venues_to_close:
            list of leisure venues that will close
        """

        super().__init__(start_time, end_time)
        self.venues_to_close = venues_to_close

    def is_active(self, date: datetime.datetime) -> bool:
        """
        Returns true if the policy is active, false otherwise

        Parameters
        ----------
        date:
            date to check
        """
        return self.start_time <= date <= self.end_time


    def apply(self, date: datetime.datetime, leisure: Leisure):
        if self.is_active(date):
            for venue in self.venues_to_close:
                leisure.closed_venues.add(venue)
            if self.end_time == date:
                for venue in self.venues_to_close:
                    leisure.closed_venues.remove(venue)



class ChangeLeisureProbability(LeisurePolicy):
    def __init__(
        self,
        start_time: str,
        end_time: str,
        leisure_activities_probabilities: Dict[str, Dict[str, Dict[str, float]]],
    ):
        """
        Changes the probability of the specified leisure activities.

        Parameters
        ----------
        - start_time : starting time of the policy.
        - end_time : end time of the policy.
        - leisure_activities_probabilities : dictionary where the first key is an age range, and the second  a
            number with the new probability for the activity in that age. Example:
            * leisure_activities_probabilities = {"pubs" : {"men" :{"0-50" : 0.5, "50-99" : 0.2}, "women" : {"0-70" : 0.2, "71-99" : 0.8}}}
        """
        super().__init__(start_time, end_time)
        self.leisure_probabilities = {}
        self.original_leisure_probabilities = None
        for activity in leisure_activities_probabilities:
            self.leisure_probabilities[activity] = {}
            self.leisure_probabilities[activity]["men"] = parse_age_probabilities(
                leisure_activities_probabilities[activity]["men"]
            )
            self.leisure_probabilities[activity]["women"] = parse_age_probabilities(
                leisure_activities_probabilities[activity]["women"]
            )

    def apply(self, date: datetime.datetime, leisure: Leisure):
        """
        Changes probabilities of doing leisure activities according to the policies specified.
        The current probabilities are stored in the policies, and restored at the end of the policy 
        time span. Keep this in mind when trying to stack policies that modify the same social venue.
        """
        if self.original_leisure_probabilities is None:
            self.original_leisure_probabilities = defaultdict(dict)
            for activity in self.leisure_probabilities:
                if activity not in leisure.leisure_distributors:
                    raise PolicyError(
                        "Trying to change leisure probability for a non-existing activity"
                    )
                activity_distributor = leisure.leisure_distributors[activity]
                self.original_leisure_probabilities[activity][
                    "men"
                ] = activity_distributor.male_probabilities
                self.original_leisure_probabilities[activity][
                    "women"
                ] = activity_distributor.female_probabilities
        if self.is_active(date):
            for activity in self.leisure_probabilities:
                activity_distributor = leisure.leisure_distributors[activity]
                activity_distributor.male_probabilities = self.leisure_probabilities[
                    activity
                ][
                    "men"
                ]
                activity_distributor.female_probabilities = self.leisure_probabilities[
                    activity
                ][
                    "women"
                ]
        else:
            # use original probabilities
            for activity in self.leisure_probabilities:
                if activity not in leisure.leisure_distributors:
                    raise PolicyError(
                        "Trying to restore a leisure probability for a non-existing activity"
                    )
                activity_distributor = leisure.leisure_distributors[activity]
                activity_distributor.male_probabilities = self.original_leisure_probabilities[
                    activity
                ][
                    "men"
                ]
                activity_distributor.female_probabilities = self.original_leisure_probabilities[
                    activity
                ][
                    "women"
                ]


