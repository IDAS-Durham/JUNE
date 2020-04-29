import warnings
import numpy as np
from scipy.stats import rv_discrete
from tqdm.auto import tqdm

from covid.groups import Group
from covid.groups.people import Person

class BoundaryError(BaseException):
    """Class for throwing boundary related errors."""
    pass


class Boundary(Group):
    """
    """

    def __init__(self, world):
        super().__init__("Boundary", "boundary")
        self.world = world
        self.n_residents = 0
        self.missing_workforce_nr()

    def missing_workforce_nr(self):
        """
        Estimate missing workforce in simulated region.
        This will establish the number of workers recruited
        from the boundary.
        """

        self._init_random_variables()

        for company in world.companies.members:
            # nr. of missing workforce
            #TODO companies shouldn always be completely full
            n_residents += (company.n_employees_max - company.n_employees)

            sex_random_array = self.sex_rv.rvs(size=n_residents)
            nomis_bin_random_array = self.nomis_bin_rv.rvs(size=n_residents)

            for i in n_residents:
                
                # create new person
                person = Person(
                    self.world,
                    (i + self.n_residents),
                    'boundary',
                    company.msoa,
                    age_random, #TODO
                    nomis_bin,  #TODO
                    sex_random, #TODO
                    health_index,
                    econ_index=0,
                    mode_of_transport=None,
                )
                person.industry = company.industry
                
                # Inform groups about new person
                self.people.append(person)
                self.people.members.append(person)
                self.company.people.append(person)
                self.msoareas.members[idx].work_people.append(person)

            self.n_residents += n_residents

    def _init_random_variables(self):
        """
        Read the frequencies for different attributes of the whole
        simulated region, and initialize random variables following
        the discrete distribution.
        """
        self.area.nomis_bin_rv
        self.area.sex_rv
