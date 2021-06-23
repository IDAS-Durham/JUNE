from june.utils import parse_age_probabilities
from . import Covid19, B117, B16172

default_susceptibility_dict = {
    Covid19.infection_id(): {"0-13": 0.5, "13-100": 1.0},
    B117.infection_id(): {"0-13": 0.5, "13-100": 1.0},
    B16172.infection_id(): {"0-13": 0.5, "13-100": 1.0},
}

class SusceptibilitySetter:
    """
    Sets susceptibilities for different viruses.

    Parameters
    ----------
    susceptibility_dict
       A dictionary mapping infection_id -> susceptibility by age.
       Example:
        susceptibility_dict = {"123" : {"0-50" : 0.5, "50-100" : 0.2}}
    """

    def __init__(self, susceptibility_dict: dict = default_susceptibility_dict):
        if susceptibility_dict is None:
            self.susceptibility_dict = {}
        else:
            self.susceptibility_dict = self._read_susceptibility_dict(
                susceptibility_dict
            )

    def _read_susceptibility_dict(self, susceptibility_dict):
        ret = {}
        for inf_id in susceptibility_dict:
            ret[inf_id] = parse_age_probabilities(
                susceptibility_dict[inf_id], fill_value=1.0
            )
        return ret

    def set_susceptibilities(self, population):
        for person in population:
            for inf_id in self.susceptibility_dict:
                if person.age >= len(self.susceptibility_dict[inf_id]):
                    continue
                person.immunity.susceptibility_dict[inf_id] = self.susceptibility_dict[
                    inf_id
                ][person.age]
