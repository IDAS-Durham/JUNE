import datetime
import numpy as np
from typing import Union, Optional, List, Dict

from .policy import Policy, PolicyCollection, PolicyError
from june.groups.leisure.social_venue_distributor import parse_age_probabilites
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
    def __init__(self, policies: List[LeisurePolicy]):
        self.policies = policies

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

    def apply(self, date: datetime.datetime, leisure: Leisure):
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
        self.original_leisure_probabilities = {}
        for activity in leisure_activities_probabilities:
            self.leisure_probabilities[activity] = {}
            self.leisure_probabilities[activity]["men"] = parse_age_probabilites(
                leisure_activities_probabilities[activity]["men"]
            )
            self.leisure_probabilities[activity]["women"] = parse_age_probabilites(
                leisure_activities_probabilities[activity]["women"]
            )
            self.original_leisure_probabilities[
                activity
            ] = {}  # this will be filled when coupled to leisure

    def is_active(self, date: datetime.datetime) -> bool:
        """
        This is modified in this policy to include the end date.
        """
        return self.start_time <= date <= self.end_time

    def apply(self, date: datetime.datetime, leisure: Leisure):
        """
        Changes probabilities of doing leisure activities according to the policies specified.
        The current probabilities are stored in the policies, and restored at the end of the policy 
        time span. Keep this in mind when trying to stack policies that modify the same social venue.
        """
        #active_policies = self.get_change_leisure_probabilities_policies(date)
        #for policy in active_policies:
        if self.start_time == date:
            # activate policy
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
                activity_distributor.male_probabilities = self.policy.leisure_probabilities[
                    activity
                ][
                    "men"
                ]
                activity_distributor.female_probabilities = self.leisure_probabilities[
                    activity
                ][
                    "women"
                ]
        elif self.end_time == date:
            # restore policy
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


