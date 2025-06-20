import datetime

from .policy import Policy, PolicyCollection
from june.interaction import Interaction
from collections import defaultdict


class InteractionPolicy(Policy):
    policy_type = "interaction"


class InteractionPolicies(PolicyCollection):
    policy_type = "interaction"

    def apply(self, date: datetime, interaction: Interaction):
        print(f"\n=== Applying Interaction Policies on {date} ===")
        
        # Get active policies
        active_policies = self.get_active(date)
        print(f"Active Policies: {active_policies}")

        # Initialize beta reductions
        beta_reductions = defaultdict(lambda: 1.0)

        # Apply active policies and update beta reductions
        for policy in active_policies:
            beta_reductions_dict = policy.apply()
            print(f"Policy {policy} produced beta reductions: {beta_reductions_dict}")

            for group in beta_reductions_dict:
                beta_reductions[group] *= beta_reductions_dict[group]

        # Assign final reductions to the interaction
        interaction.beta_reductions = beta_reductions
        print(f"Final beta reductions assigned to interaction: {dict(interaction.beta_reductions)}")


class SocialDistancing(InteractionPolicy):
    policy_subtype = "beta_factor"

    def __init__(self, start_time: str, end_time: str, beta_factors: dict = None):
        super().__init__(start_time, end_time)
        self.beta_factors = beta_factors

    def apply(self):        
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
        return self.beta_factors


class MaskWearing(InteractionPolicy):
    policy_subtype = "beta_factor"

    def __init__(
        self,
        start_time: str,
        end_time: str,
        compliance: float,
        beta_factor: float,
        mask_probabilities: dict = None,
    ):
        super().__init__(start_time, end_time)
        self.compliance = compliance
        self.beta_factor = beta_factor
        self.mask_probabilities = mask_probabilities

    def apply(self):
        """
        Implement mask wearing policy

        -----------
        Parameters:
        betas: e.g. (dict) from DefaultInteraction, e.g. DefaultInteraction.from_file(selector=selector).beta

        Assumptions:
        - Currently we assume that mask wearing is implemented in a similar way to social distanding
          but with a mean field effect in beta reduction
        - Currently we assume that the changes are group dependent
        """
        ret = {}
        for key, value in self.mask_probabilities.items():
            ret[key] = 1 - (value * self.compliance * (1 - self.beta_factor))
        return ret
