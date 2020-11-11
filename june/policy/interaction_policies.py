import datetime
from copy import deepcopy

from .policy import Policy, PolicyCollection, Policies
from june.interaction import Interaction
from collections import defaultdict


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
    original_betas = None

    def apply(self, date: datetime, interaction: Interaction, regional_compliance=None):
        # order matters, first deactivate all policies that expire in this day.
        interaction.regional_compliance = regional_compliance
        interaction.distanced_groups = set()
        active_policies = self.get_active(date)
        if self.original_betas is None:
            self.original_betas = deepcopy(interaction.beta)
        if not active_policies:
            interaction.beta = deepcopy(self.original_betas)
            return 
        beta_reductions = defaultdict(lambda: 1.0)
        for policy in active_policies:
            beta_reductions_dict = policy.apply()
            for group in beta_reductions_dict:
                if beta_reductions_dict[group] != 1.:
                    interaction.distanced_groups.add(group)
                beta_reductions[group] *= beta_reductions_dict[group]
        for group in beta_reductions:
            if group != "household_visits":
                interaction.beta[group] = self.original_betas[group] * beta_reductions[group]
        interaction.original_betas = self.original_betas
        interaction.beta_reductions = beta_reductions
        
class SocialDistancing(InteractionPolicy):
    def __init__(
        self,
        start_time: str,
        end_time: str,
        beta_factors: dict = None,
    ):
        super().__init__(start_time, end_time)
        self.policy_subtype = "beta_factor"
        self.original_betas = None
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
    def __init__(
        self,
        start_time: str,
        end_time: str,
        compliance: float,
        beta_factor: float,    
        mask_probabilities: dict = None,
    ):
        super().__init__(start_time, end_time)
        self.policy_subtype = "beta_factor"
        self.original_betas = None
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
            ret[key] = (1 - (value * self.compliance * (1-self.beta_factor)))
        return ret

