from typing import Optional
from june.utils import (
    parse_age_probabilities,
    parse_prevalence_comorbidities_in_reference_population,
    read_comorbidity_csv,
    convert_comorbidities_prevalence_to_dict,
)
from . import Covid19, B117, B16172

default_multiplier_dict = {
    Covid19.infection_id(): 1.0,
    B117.infection_id(): 1.5,
    B16172.infection_id(): 1.5,
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
        self,
        multiplier_dict: dict = default_multiplier_dict,
        multiplier_by_comorbidity: Optional[dict] = None,
        comorbidity_prevalence_reference_population: Optional[dict] = None,
    ):
        if multiplier_dict is None:
            self.multiplier_dict = {}
        else:
            self.multiplier_dict = multiplier_dict
        self.multiplier_by_comorbidity = multiplier_by_comorbidity
        if comorbidity_prevalence_reference_population is not None:
            self.comorbidity_prevalence_reference_population = (
                parse_prevalence_comorbidities_in_reference_population(
                    comorbidity_prevalence_reference_population
                )
            )
        else:
            self.comorbidity_prevalence_reference_population = None

    @classmethod
    def from_file_with_comorbidities(
        cls,
        multiplier_dict: dict = default_multiplier_dict,
        comorbidity_multipliers_path: Optional[str] = None,
        male_comorbidity_reference_prevalence_path: Optional[str] = None,
        female_comorbidity_reference_prevalence_path: Optional[str] = None,
    ) -> "EffectiveMultiplierSetter":
        if comorbidity_multipliers_path is not None:
            with open(comorbidity_multipliers_path) as f:
                comorbidity_multipliers = yaml.load(f, Loader=yaml.FullLoader)
            female_prevalence = read_comorbidity_csv(
                female_comorbidity_reference_prevalence_path
            )
            male_prevalence = read_comorbidity_csv(
                male_comorbidity_reference_prevalence_path
            )
            comorbidity_prevalence_reference_population = (
                convert_comorbidities_prevalence_to_dict(
                    female_prevalence, male_prevalence
                )
            )
        else:
            comorbidity_multipliers = None
            comorbidity_prevalence_reference_population = None
        return EffectiveMultiplierSetter(
            multiplier_dict=multiplier_dict,
            multiplier_by_comorbidity=comorbidity_multipliers,
            comorbidity_prevalence_reference_population=comorbidity_prevalence_reference_population,
        )

    def get_multiplier_from_reference_prevalence(self, age, sex):
        """
        Compute mean comorbidity multiplier given the prevalence of the different comorbidities
        in the reference population (for example the UK). It will be used to remove effect of
        comorbidities in the reference population
        Parameters
        ----------
        age:
            age group to compute average multiplier
        sex:
            sex group to compute average multiplier
        Returns
        -------
            weighted_multiplier:
                weighted mean of the multipliers given prevalence
        """
        weighted_multiplier = 0.0
        for comorbidity in self.comorbidity_prevalence_reference_population.keys():
            weighted_multiplier += (
                self.multiplier_by_comorbidity[comorbidity]
                * self.comorbidity_prevalence_reference_population[comorbidity][sex][
                    age
                ]
            )
        return weighted_multiplier

    def get_weighted_multipliers_by_age_sex(
        self,
    ):
        reference_multipliers = {"m": [], "f": []}
        for sex in ("m", "f"):
            for age in range(100):
                reference_multipliers[sex].append(
                    self.get_multiplier_from_reference_prevalence(age=age, sex=sex)
                )
        return reference_multipliers

    def set_multipliers(self, population):
        if (
            self.multiplier_by_comorbidity is not None
            and self.comorbidity_prevalence_reference_population is not None
        ):
            set_comorbidity_multipliers = True
            reference_weighted_multipliers = self.get_weighted_multipliers_by_age_sex()
        else:
            set_comorbidity_multipliers = False
        for person in population:
            for inf_id in self.multiplier_dict:
                person.immunity.effective_multiplier_dict[
                    inf_id
                ] = self.multiplier_dict[inf_id]
                if set_comorbidity_multipliers:
                    multiplier = self.multiplier_by_comorbidity.get(
                        person.comorbidity, 1.0
                    )
                    reference_multiplier = reference_weighted_multipliers[person.sex][
                        person.age
                    ]
                    person.immunity.effective_multiplier_dict[inf_id] += (
                        multiplier / reference_multiplier
                    ) - 1.0
