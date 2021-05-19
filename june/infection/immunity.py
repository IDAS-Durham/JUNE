class Immunity:
    """
    This class stores the "medical record" of the person,
    indicating which infections the person has recovered from.
    """

    __slots__ = "susceptibility", "recovered_infections_ids"

    def __init__(self):
        self.recovered_infections_ids = set()

    def add_immunity(self, infection_id):
        self.recovered_infections_ids.add(infection_id)

    def is_immune(self, infection_id):
        return infection_id in self.recovered_infections_ids
