from collections import defaultdict


class Immunity:
    """
    This class stores the "medical record" of the person,
    indicating which infections the person has recovered from.
    """

    __slots__ = "susceptibility_dict"

    def __init__(self, susceptibility_dict: dict = None):
        self.susceptibility_dict = defaultdict(lambda: 1.0)
        if susceptibility_dict:
            for key, value in susceptibility_dict.items():
                self.susceptibility_dict[key] = value

    def add_immunity(self, infection_ids):
        for infection_id in infection_ids:
            self.susceptibility_dict[infection_id] = 0.0

    def serialize(self):
        return list(self.susceptibility_dict.keys()), list(
            self.susceptibility_dict.values()
        )

    def is_immune(self, infection_id):
        return self.susceptibility_dict[infection_id] == 0.0
