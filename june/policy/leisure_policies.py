import datetime
from copy import deepcopy
import numpy as np
from collections import defaultdict
from typing import Dict, Union

from .policy import Policy, Policies, PolicyCollection
from june.exc import PolicyError
from june.utils.parse_probabilities import parse_age_probabilities
from june.groups.leisure import Leisure


class LeisurePolicy(Policy):
    policy_type = "leisure"

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
        """
        Applies all the leisure policies. Each Leisure policy will change the probability of
        doing a certain leisure activity. For instance, closing Pubs sets the probability of
        going to the Pub to zero. We store a dictionary with the relative reductions in leisure
        probabilities per activity, and this dictionary is then looked at by the leisure module.

        This is very similar to how we deal with social distancing / mask wearing policies.
        """
        for region in leisure.regions:
            region.policy["global_closed_venues"] = set()
        leisure.policy_reductions = {}
        if "residence_visits" in leisure.leisure_distributors:
            leisure.leisure_distributors["residence_visits"].policy_reductions = {}
        change_leisure_probability_policies_counter = 0
        for policy in self.get_active(date):
            if policy.policy_subtype == "change_leisure_probability":
                change_leisure_probability_policies_counter += 1
                if change_leisure_probability_policies_counter > 1:
                    raise ValueError(
                        "Having more than one change leisure probability policy"
                        "active is not supported."
                    )
                leisure.policy_reductions = policy.apply(leisure=leisure)
            else:
                policy.apply(leisure=leisure)


class CloseLeisureVenue(LeisurePolicy):
    policy_subtype = "close_venues"

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

    def apply(self, leisure: Leisure):
        for region in leisure.regions:
            for venue in self.venues_to_close:
                region.policy["global_closed_venues"].add(venue)


class ChangeLeisureProbability(LeisurePolicy):
    policy_subtype = "change_leisure_probability"

    def __init__(
        self,
        start_time: str,
        end_time: str,
        activity_reductions: Dict[str, Dict[str, Dict[str, float]]],
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
        self.activity_reductions = self._read_activity_reductions(activity_reductions)

    def _read_activity_reductions(self, activity_reductions):
        ret = {}
        day_types = ["weekday", "weekend"]
        sexes = ["male", "female"]
        _sex_t = {"male": "m", "female": "f"}
        for activity, pp in activity_reductions.items():
            ret[activity] = {}
            ret[activity]["weekday"] = {}
            ret[activity]["weekend"] = {}
            for first_entry in pp:
                if first_entry in ["weekday", "weekend"]:
                    day_type = first_entry
                    if "both_sexes" in pp[day_type]:
                        for sex in sexes:
                            june_sex = _sex_t[sex]
                            probs = parse_age_probabilities(
                                activity_reductions[activity][day_type]["both_sexes"]
                            )
                            ret[activity][day_type][june_sex] = probs
                    else:
                        for sex in sexes:
                            june_sex = _sex_t[sex]
                            probs = parse_age_probabilities(
                                activity_reductions[activity][day_type][sex]
                            )
                            ret[activity][day_type][june_sex] = probs
                elif first_entry == "any" or first_entry in ["male", "female"]:
                    for sex in sexes:
                        june_sex = _sex_t[sex]
                        probs = parse_age_probabilities(
                            activity_reductions[activity][sex]
                        )
                        for day_type in day_types:
                            ret[activity][day_type][june_sex] = probs
                elif first_entry == "both_sexes":
                    for sex in sexes:
                        june_sex = _sex_t[sex]
                        probs = parse_age_probabilities(
                            activity_reductions[activity]["both_sexes"]
                        )
                        for day_type in day_types:
                            ret[activity][day_type][june_sex] = probs
                else:
                    for day_type in day_types:
                        for sex in sexes:
                            june_sex = _sex_t[sex]
                            ret[activity][day_type][june_sex] = parse_age_probabilities(
                                activity_reductions[activity][day_type][sex]
                            )
        return ret

    def apply(self, leisure: Leisure):
        return self.activity_reductions


class ChangeVisitsProbability(LeisurePolicy):
    policy_subtype = "change_visits_probability"

    def __init__(
        self,
        start_time: str,
        end_time: str,
        new_residence_type_probabilities: Dict[str, float],
    ):
        """
        Changes the probability of the specified leisure activities.

        Parameters
        ----------
        - start_time : starting time of the policy.
        - end_time : end time of the policy.
        - new_residence_type_probabilities
            new probabilities for residence visits splits, eg, {"household" : 0.8, "care_home" : 0.2}
        """
        super().__init__(start_time, end_time)
        self.policy_reductions = new_residence_type_probabilities

    def apply(self, leisure: Leisure):
        leisure.leisure_distributors[
            "residence_visits"
        ].policy_reductions = self.policy_reductions
