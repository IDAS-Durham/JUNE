import datetime

from .policy import Policy, PolicyCollection, Policies
from june.interaction import Interaction
from typing import Union, Optional, List, Dict


class InteractionPolicy(Policy):
    def __init__(
        self,
        start_time: str,
        end_time: str,
    ):
        super().__init__(start_time=start_time, end_time=end_time)
        self.policy_type = "interaction"

class InteractionPolicies(PolicyCollection):
    policy_type = "interaction"

    def apply(self, date: datetime, interaction: Interaction):
        # order matters, first deactivate all policies that expire in this day.
        for policy in self.policies:
            if policy.end_time == date:
                policy.apply(date=date, interaction=interaction)
        # now activate all policies that need to be activated
        for policy in self.policies:
            if policy.start_time == date:
                policy.apply(date=date, interaction=interaction)

class SocialDistancing(InteractionPolicy):
    def __init__(
        self,
        start_time: str,
        end_time: str,
        beta_factors: dict = None,
    ):
        super().__init__(start_time, end_time)
        self.original_betas = {}
        self.beta_factors = beta_factors
        for key in beta_factors:
            self.original_betas[key] = None  # to be filled when coupled to interaction

    def apply(self, date: datetime, interaction: Interaction):
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
        print(date)
        if self.end_time == date:  # deactivate policy, restore betas.
            for key, value in self.original_betas.items():
                interaction.beta[key] = value

        if self.start_time == date:  # activate policy, save current betas.
            print("changing...")
            for key, value in self.beta_factors.items():
                self.original_betas[key] = interaction.beta[key]
                interaction.beta[key] = interaction.beta[key] * value

