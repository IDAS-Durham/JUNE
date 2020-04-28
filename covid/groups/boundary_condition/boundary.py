import warnings
import numpy as np
import pandas as pd
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
        self.people = []
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

            nomis_bin_random_array = self.nomis_bin_rv.rvs(size=n_residents)
            self.area.sex_rv = stats.rv_discrete(
                values=(
                    np.arange(0, len(sex_freq_per_compsec.columns.values)),
                    sex_freq.values
                )
            )

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

        # sex-frequencies per company sector
        f_col = [
            col for col in self.world.inputs.compsec_by_sex_df.columns.values if "f " in col
        ]
        f_nrs_per_compsec = self.world.inputs.compsec_by_sex_df[f_col].sum(axis='rows')
        
        m_col = [
            col for col in self.world.inputs.compsec_by_sex_df.columns.values if "m " in col
        ]
        m_nrs_per_compsec = self.world.inputs.compsec_by_sex_df[m_col].sum(axis='rows')

        self.sex_freq_per_compsec = pd.DataFrame(
            data=np.vstack((f_nrs_per_compsec.values, m_nrs_per_compsec.values)).T,
            index=[idx.split(' ')[-1] for idx in m_nrs_per_compsec.index.values],
            columns=["f", "m"],
        )

        # age-frequencies based on the whole simulated region
        nomis_and_age_list = [
            [person.nomis_bin, person.age] for person in self.world.people.members
        ]
        nomis_bin_arr, age_arr = np.array(nomis_and_age_list).T
        (nomis_bin_unique, nomis_bin_counts) = np.unique(nomis_bin_arr, return_counts=True)
        (age_unique, age_counts) = np.unique(age_arr, return_counts=True)

        self.nomis_bin_freq = pd.DataFrame(
            data=nomis_bin_counts,
            index=list(nomis_bin_unique),
            columns=["freq"],
        )
        self.age_freq = pd.DataFrame(
            data=age_counts,
            index=list(age_unique),
            columns=["freq"],
        )
