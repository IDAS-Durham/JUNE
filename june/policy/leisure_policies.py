import datetime
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
        leisure.closed_venues = set()
        leisure.policy_poisson_parameters = {}
        change_leisure_probability_policies_counter = 0
        for policy in self.get_active(date):
            if policy.policy_subtype == "change_leisure_probability":
                change_leisure_probability_policies_counter += 1
                if change_leisure_probability_policies_counter > 1:
                    raise ValueError(
                        "Having more than one change leisure probability policy"
                        "active is not supported."
                    )
                leisure.policy_poisson_parameters = policy.apply(leisure=leisure)
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
        for venue in self.venues_to_close:
            leisure.closed_venues.add(venue)


class ChangeLeisureProbability(LeisurePolicy):
    policy_subtype = "change_leisure_probability"

    def __init__(
        self,
        start_time: str,
        end_time: str,
        new_leisure_poisson_parameters: Dict[str, Dict[str, Dict[str, float]]],
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
        self.poisson_parameters = self._read_poisson_parameters(
            new_leisure_poisson_parameters
        )

    def _read_poisson_parameters(self, new_leisure_poisson_parameters):
        ret = {}
        day_types = ["weekday", "weekend"]
        sexes = ["male", "female"]
        _sex_t = {"male": "m", "female": "f"}
        for activity, pp in new_leisure_poisson_parameters.items():
            ret[activity] = {}
            ret[activity]["weekday"] = {}
            ret[activity]["weekend"] = {}
            for day_type in pp:
                if day_type == "any" or day_type in ["male", "female"]:
                    for sex in sexes:
                        june_sex = _sex_t[sex]
                        probs = parse_age_probabilities(
                            new_leisure_poisson_parameters[activity][sex]
                        )
                        for day_type in day_types:
                            ret[activity][day_type][june_sex] = probs
                else:
                    for day_type in day_types:
                        for sex in sexes:
                            june_sex = _sex_t[sex]
                            ret[activity][day_type][june_sex] = parse_age_probabilities(
                                new_leisure_poisson_parameters[activity][day_type][sex]
                            )
        return ret

    def apply(self, leisure: Leisure):
        """
        Changes probabilities of doing leisure activities according to the policies specified.
        The current probabilities are stored in the policies, and restored at the end of the policy
        time span. Keep this in mind when trying to stack policies that modify the same social venue.
        """
        return self.poisson_parameters
