import logging

import numpy as np
import pandas as pd
from scipy.stats import rv_discrete

from june.demography.person import Person
from june.groups import Group

logger = logging.getLogger(__name__)


class BoundaryError(BaseException):
    """Class for throwing boundary related errors."""


class Boundary(Group):
    def __init__(self, world):
        super().__init__()
        self.world = world
        self.n_residents = 0
        self.missing_workforce_nr()

    def missing_workforce_nr(self):
        """
        Estimate missing workforce in simulated region.
        This will establish the number of workers recruited
        from the boundary.
        """

        self.ADULT_THRESHOLD = self.world.config["people"]["adult_threshold"]
        self.OLD_THRESHOLD = self.world.config["people"]["old_threshold"]
        self._init_frequencies()

        for company in self.world.companies.members:
            # nr. of missing workforce
            # TODO companies shouldn always be completely full
            n_residents = (company.n_employees_max - company.n_employees)

            (
                sex_rnd_arr, nomis_bin_rnd_arr, age_rnd_arr
            ) = self.init_random_variables(n_residents, company.industry)

            for i in range(n_residents):
                # create new person
                person = Person(
                    self.world,
                    (i + self.n_residents),
                    'boundary',
                    company.msoa,
                    age_rnd_arr[i],
                    nomis_bin_rnd_arr[i],
                    sex_rnd_arr[i],
                    econ_index=0,
                    mode_of_transport=None,
                )
                person.industry = company.industry

                # Inform groups about new person
                self.people.append(person)
                self.world.people.members.append(person)
                company.people.append(person)
                idx = [
                    idx for idx, msoa in enumerate(self.world.msoareas.members)
                    if msoa.name == company.msoa
                ][0]
                self.world.msoareas.members[idx].work_people.append(person)

            self.n_residents += n_residents

    def _init_frequencies(self):
        """
        Create the frequencies for different attributes of the whole
        simulated region.
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

        sex_freq_per_compsec = pd.DataFrame(
            data=np.vstack((f_nrs_per_compsec.values, m_nrs_per_compsec.values)).T,
            index=[idx.split(' ')[-1] for idx in m_nrs_per_compsec.index.values],
            columns=["f", "m"],
        )
        self.sex_freq_per_compsec = sex_freq_per_compsec.div(
            sex_freq_per_compsec.sum(axis=1), axis=0,
        )

        # age-frequencies of people at work, based on the whole simulated region
        nomis_and_age_list = [
            [person.nomis_bin, person.age] for person in self.world.people.members
        ]
        nomis_bin_arr, age_arr = np.array(nomis_and_age_list).T
        nomis_bin_unique, nomis_bin_counts = np.unique(nomis_bin_arr, return_counts=True)
        age_unique, age_counts = np.unique(age_arr, return_counts=True)

        nomis_bin_df = pd.DataFrame(
            data=np.vstack((nomis_bin_unique, nomis_bin_counts)).T,
            columns=["age", "freq"],
        )
        nomis_bin_df = nomis_bin_df[
            (nomis_bin_df["age"] >= self.ADULT_THRESHOLD) & \
            (nomis_bin_df["age"] <= self.OLD_THRESHOLD)
            ]
        self.nomis_bins = nomis_bin_df.div(nomis_bin_df.sum(axis=0), axis=1)

        age_df = pd.DataFrame(
            data=np.vstack((age_unique, age_counts)).T,
            columns=["age", "freq"],
        )
        age_df = age_df[
            (age_df["age"] >= 20) & \
            (age_df["age"] <= 65)
            ]
        self.ages = age_df.div(age_df.sum(axis=0), axis=1)

    def init_random_variables(self, n_residents, compsec):
        """
        Create the random variables following the discrete distributions.
        for different attributes of the whole simulated region.
        """
        sex_rv = rv_discrete(
            values=(
                np.arange(0, 2),
                self.sex_freq_per_compsec.loc[compsec].values,
            )
        )
        sex_rnd_arr = sex_rv.rvs(size=n_residents)

        nomis_bin_rv = rv_discrete(
            values=(np.arange(len(self.nomis_bins.freq.values)), self.nomis_bins.freq.values)
        )
        nomis_bin_rnd_arr = nomis_bin_rv.rvs(size=n_residents)

        age_rv = rv_discrete(
            values=(np.arange(len(self.ages.freq.values)), self.ages.freq.values)
        )
        age_rnd_arr = age_rv.rvs(size=n_residents)

        return sex_rnd_arr, nomis_bin_rnd_arr, age_rnd_arr
