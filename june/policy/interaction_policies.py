import datetime

from .policy import Policy, PolicyCollection
from june.interaction import Interaction
from typing import Union, Optional, List, Dict


class InteractionPolicy(Policy):
    def __init__(
        self,
        start_time: Union[str, datetime.datetime],
        end_time: Union[str, datetime.datetime],
    ):
        super().__init__(start_time=start_time, end_time=end_time)
        self.policy_type = "interaction"

class InteractionPolicies(PolicyCollection):
    def __init__(self, policies: List[InteractionPolicy]):
        super().__init__(policies=policies)

class SocialDistancing(InteractionPolicy):
    def __init__(
        self,
        start_time: Union[str, datetime.datetime],
        end_time: Union[str, datetime.datetime],
        beta_factors: dict = None,
    ):
        super().__init__(start_time, end_time)
        self.original_betas = {}
        self.beta_factors = beta_factors
        for key in beta_factors.keys():
            self.original_betas[key] = None  # to be filled when coupled to interaction

    def apply(self, date, interaction: Interaction):
        """
        Implement social distancing policy
        
        -----------
        Parameters:
        betas: e.g. (dict) from DefaultInteraction, e.g. DefaultInteraction.from_file(selector=selector).beta

        Assumptions:
        - Currently we assume that social distancing is implemented first and this affects all
          interactions and intensities globally
        - Currently we assume that the changes are not group dependent
        TODO:
        - Implement structure for people to adhere to social distancing with a certain compliance
        - Check per group in config file
        """
        social_distancing_policies = self.get_social_distancing_policies(date)
        # order matters, first deactivate all policies that expire in this day.
        for policy in social_distancing_policies:
            if policy.end_time == date:  # deactivate policy, restore betas.
                for key, value in policy.original_betas.items():
                    interaction.beta[key] = value

        # now activate all policies that need to be activated
        for policy in social_distancing_policies:
            if policy.start_time == date:  # activate policy, save current betas.
                for key, value in policy.beta_factors.items():
                    policy.original_betas[key] = interaction.beta[key]
                    interaction.beta[key] = interaction.beta[key] * value

