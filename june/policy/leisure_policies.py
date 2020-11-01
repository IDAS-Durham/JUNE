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
    original_leisure_probabilities_per_venue = None

    def apply(self, date: datetime, leisure: Leisure, regional_compliance: Dict=None):
        """
        Applies leisure policies. There are currently two types of leisure policies
        implemented: CloseLeisureVenue, and ChangeLeisureProbability. To ensure
        compatibility when adding multiple policies of the same type, we "clear" the
        leisure module at the beginning of each application, ie, we set closed_venues = set(),
        and the original probabilities for each social venue distributor. We then apply 
        the policies currently active at the given date.
        """
        if self.original_leisure_probabilities_per_venue is None:
            self.original_leisure_probabilities_per_venue = defaultdict(dict)
            # first time step, save originals
            for distributor in leisure.leisure_distributors.values():
                self.original_leisure_probabilities_per_venue[distributor.spec][
                    "men"
                ] = distributor.male_probabilities
                self.original_leisure_probabilities_per_venue[distributor.spec][
                    "women"
                ] = distributor.female_probabilities
        else:
            # set sv distributors to original values
            for distributor in leisure.leisure_distributors.values():
                distributor.male_probabilities = self.original_leisure_probabilities_per_venue[
                    distributor.spec
                ][
                    "men"
                ]
                distributor.female_probabilities = self.original_leisure_probabilities_per_venue[
                    distributor.spec
                ][
                    "women"
                ]
        leisure.closed_venues = set()
        active_policies = self.get_active(date=date)
        for policy in active_policies:
            policy.apply(leisure=leisure, regional_compliance=regional_compliance)


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

    def apply(self, leisure: Leisure, regional_compliance = None):
        for venue in self.venues_to_close:
            leisure.closed_venues.add(venue)


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
        for activity in leisure_activities_probabilities:
            self.leisure_probabilities[activity] = {}
            self.leisure_probabilities[activity]["men"] = parse_age_probabilities(
                leisure_activities_probabilities[activity]["men"]
            )
            self.leisure_probabilities[activity]["women"] = parse_age_probabilities(
                leisure_activities_probabilities[activity]["women"]
            )

    def apply(self, leisure: Leisure, regional_compliance=None):
        """
        Changes probabilities of doing leisure activities according to the policies specified.
        The current probabilities are stored in the policies, and restored at the end of the policy 
        time span. Keep this in mind when trying to stack policies that modify the same social venue.
        """
        leisure.regional_compliance = regional_compliance
        for activity in self.leisure_probabilities:
            activity_distributor = leisure.leisure_distributors[activity]
            activity_distributor.male_probabilities = self.leisure_probabilities[
                activity
            ]["men"]
            activity_distributor.female_probabilities = self.leisure_probabilities[
                activity
            ]["women"]
