from june.utils import parse_age_probabilities
from . import Covid19, B117

default_multiplier_dict = {
    Covid19.infection_id(): 1.0,
    B117.infection_id(): 1.5,
}


class EffectiveMultiplierSetter:
    """
    Sets effective multipliers that increment or decrease the probability
    of developing a severe infection. This multipliers can arise due to a person's
    comorbidities, or due to different variants producing different outcomes.

    Parameters
    ----------
    multiplier_dict
       A dictionary mapping infection_id -> multiplier.
       Example:
        multiplier_dict = {"123" : 1.3}
    """

    # Varying due to comorbidities

    # Varying due to different variants

    def __init__(
        self, multiplier_dict: dict = default_multiplier_dict, comorbidities=False
    ):
        if multiplier_dict is None:
            self.multiplier_dict = {}
        else:
            self.multiplier_dict = multiplier_dict
        # if comorbidities:
        #    continue

    def set_multipliers(self, population):
        for person in population:
            for inf_id in self.multiplier_dict:
                person.immunity.effective_multiplier_dict[
                    inf_id
                ] = self.multiplier_dict[inf_id]
