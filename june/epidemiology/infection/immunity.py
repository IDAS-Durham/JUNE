from collections import defaultdict


class Immunity:
    """
    This class stores the "medical record" of the person,
    indicating which infections the person has recovered from.
    """

    __slots__ = "susceptibility_dict", "effective_multiplier_dict"

    def __init__(self, susceptibility_dict: dict = None, effective_multiplier_dict: dict=None):
        if susceptibility_dict:
            self.susceptibility_dict = susceptibility_dict
        else:
            self.susceptibility_dict = {}
        if effective_multiplier_dict:
            self.effective_multiplier_dict = effective_multiplier_dict
        else:
            self.effective_multiplier_dict = {}

    def add_immunity(self, infection_ids):
        for infection_id in infection_ids:
            self.susceptibility_dict[infection_id] = 0.0

    def add_multiplier(self, infection_id, multiplier):
        self.effective_multiplier_dict[infection_id] = multiplier

    def get_susceptibility(self, infection_id):
        return self.susceptibility_dict.get(infection_id, 1.0)

    def get_effective_multiplier(self, infection_id):
        return self.effective_multiplier_dict.get(infection_id, 1.0)

    def serialize(self):
        return list(self.susceptibility_dict.keys()), list(
            self.susceptibility_dict.values()
        )

    def is_immune(self, infection_id):
        return self.susceptibility_dict.get(infection_id, 1.0) == 0.0
