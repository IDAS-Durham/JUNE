from .infection import InfectionSelectors, InfectionSeeds, SusceptibilitySetter
from june.demography import Population


class Epidemiology:
    """
    This class boxes all the functionality related to epidemics,
    namely the infections, infection seeds, infection selectors,
    and susceptibility setter.
    """

    def __init__(
        self,
        infection_selectors: InfectionSelectors,
        infection_seeds: InfectionSeeds,
        susceptibility_setter: SusceptibilitySetter,
    ):
        self.infection_selectors = infection_selectors
        self.infection_seeds = infection_seeds
        self.susceptibility_setter = susceptibility_setter

    def set_susceptibilities(self, population):
        self.susceptibility_setter.set_susceptibilities(population)
