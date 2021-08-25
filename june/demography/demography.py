from typing import List, Dict, Optional

import numpy as np
import pandas as pd
import h5py
import yaml

from june import paths
from june.demography import Person
from june.geography import Geography
from june.utils import random_choice_numba

default_data_path = paths.data_path / "input/demography"

default_areas_map_path = paths.data_path / "input/geography/area_super_area_region.csv"

default_config_path = paths.configs_path


def parse_age_bin(age_bin: str):
    pairs = list(map(int, age_bin.split("-")))
    return pairs


class DemographyError(BaseException):
    pass


class AgeSexGenerator:
    def __init__(
        self,
        age_counts: list,
        sex_bins: list,
        female_fractions: list,
        ethnicity_age_bins: list = None,
        ethnicity_groups: list = None,
        ethnicity_structure: list = None,
        max_age=99,
    ):
        """
        age_counts is an array where the index in the array indicates the age,
        and the value indicates the number of counts in that age.
        sex_bins are the lower edges of each sex bin where we have a fraction of females from
        census data, and female_fractions are those fractions.
        ethnicity_age_bins are the lower edges of the age bins that ethnicity data is in
        ethnicity_groups are the labels of the ethnicities which we have data for.
        ethnicity_structure are (integer) ratios of the ethnicities, for each age bin. the sum
        of this strucutre need NOT be the total number of people returned by the generator.
        Example:
            age_counts = [1, 2, 3] means 1 person of age 0, 2 people of age 1 and 3 people of age 2.
            sex_bins = [1, 3] defines two bins: (0,1) and (3, infinity)
            female_fractions = [0.3, 0.5] means that between the ages 0 and 1 there are 30% females,
                                          and there are 50% females in the bin 3+ years
            ethnicity_age_bins - see sex_bins
            ethnicity_groups = ['A','B','C'] - there are three types of ethnicities that we are
                                          assigning here.
            ethnicity_structure = [[0,5,3],[2,3,0],...] in the first age bin, we assign people
                                          ethnicities A:B:C with probability 0:5:3, and so on.
        Given this information we initialize two generators for age and sex, that can be accessed
        through gen = AgeSexGenerator().age() and AgeSexGenerator().sex().

        Parameters
        ----------
        age_counts
            A list or array with the counts for each age.
        female_fractions
            A dictionary where keys are age intervals like "int-int" and the
            values are the fraction of females inside each age bin.
        """
        self.n_residents = np.sum(age_counts)
        ages = np.repeat(np.arange(0, len(age_counts)), age_counts)
        female_fraction_bins = np.digitize(ages, bins=list(map(int, sex_bins))) - 1
        sexes = (
            np.random.uniform(0, 1, size=self.n_residents)
            < np.array(female_fractions)[female_fraction_bins]
        ).astype(int)
        sexes = map(lambda x: ["m", "f"][x], sexes)
        self.age_iterator = iter(ages)
        self.sex_iterator = iter(sexes)
        self.max_age = max_age

        if ethnicity_age_bins is not None:
            ethnicity_age_counts, _ = np.histogram(
                ages, bins=list(map(int, ethnicity_age_bins)) + [100]
            )
            ethnicities = []
            for age_ind, age_count in enumerate(ethnicity_age_counts):
                ethnicities.extend(
                    np.random.choice(
                        np.repeat(ethnicity_groups, ethnicity_structure[age_ind]),
                        age_count,
                    )
                )
            self.ethnicity_iterator = iter(ethnicities)

    @classmethod
    def from_age_sex_bins(
        cls, men_age_dict: dict, women_age_dict: dict, exponential_decay: int = 2
    ):
        """
        Initializes age and sex generator (no ethnicity and socioecon_index for now) from
        a dictionary containing age bins and counts for man and woman. An example of the input is
        men_age_dict = {"0-2" : 10, "2-99": 50}. If the bin contains the 99 value at the end,
        the age will be sampled with an exponential decay of the form e^(-x/exponential_decay).
        """
        age_counts = np.zeros(99, dtype=np.int64)
        sex_bins = []
        female_fractions = []
        for (key_man, value_man), (_, value_woman) in zip(
            men_age_dict.items(), women_age_dict.items()
        ):
            age1, age2 = parse_age_bin(key_man)
            total_people = value_man + value_woman
            sex_bins.append(age1)
            if total_people == 0:
                female_fractions.append(0)
            else:
                female_fractions.append(value_woman / total_people)
            if age2 == 99:
                exp_values = np.exp(-np.arange(0, age2 - age1 + 1) / exponential_decay)
                p = exp_values / exp_values.sum()
                age_dist = np.random.choice(
                    np.arange(age1, age2 + 1), size=total_people, p=p
                )
                ages, counts = np.unique(age_dist, return_counts=True)
                age_counts[ages] += counts
            else:
                age_dist = np.random.choice(
                    np.arange(age1, age2 + 1), size=total_people
                )
                ages, counts = np.unique(age_dist, return_counts=True)
                age_counts[ages] += counts
        return cls(age_counts, sex_bins, female_fractions)

    def age(self) -> int:
        try:
            return min(next(self.age_iterator), self.max_age)
        except StopIteration:
            raise DemographyError("No more people living here!")

    def sex(self) -> str:
        try:
            return next(self.sex_iterator)
        except StopIteration:
            raise DemographyError("No more people living here!")

    def ethnicity(self) -> str:
        try:
            return next(self.ethnicity_iterator)
        except StopIteration:
            raise DemographyError("No more people living here!")


class Population:
    def __init__(self, people: Optional[List[Person]] = None):
        """
        A population of people.

        Behaves mostly like a list but also has the name of the area attached.

        Parameters
        ----------
        people
            A list of people generated to match census data for that area
        """
        if people is None:
            self.people_dict = {}
            self.people_ids = set()
            self.people = []
        else:
            self.people_dict = {person.id: person for person in people}
            self.people_ids = set(self.people_dict.keys())
            self.people = people

    def __len__(self):
        return len(self.people)

    def __iter__(self):
        return iter(self.people)

    def __getitem__(self, index):
        return self.people[index]

    def __add__(self, population: "Population"):
        self.people.extend(population.people)
        self.people_dict = {**self.people_dict, **population.people_dict}
        self.people_ids = set(self.people_dict.keys())
        return self

    def add(self, person):
        self.people_dict[person.id] = person
        self.people.append(person)
        self.people_ids.add(person.id)

    def remove(self, person):
        del self.people_dict[person.id]
        self.people.remove(person)
        self.people_ids.remove(person.id)

    def extend(self, people):
        for person in people:
            self.add(person)

    def get_from_id(self, id):
        return self.people_dict[id]

    @property
    def members(self):
        return self.people

    @property
    def total_people(self):
        return len(self.members)

    @property
    def infected(self):
        return [person for person in self.people if person.infected]

    @property
    def dead(self):
        return [person for person in self.people if person.dead]

    @property
    def vaccinated(self):
        return [person for person in self.people if person.vaccinated]

class Demography:
    def __init__(
        self,
        area_names,
        age_sex_generators: Dict[str, AgeSexGenerator],
        comorbidity_data=None,
    ):
        """
        Tool to generate population for a certain geographical regin.

        Parameters
        ----------
        age_sex_generators
            A dictionary mapping area identifiers to functions that generate
            age and sex for individuals.
        """
        self.area_names = area_names
        self.age_sex_generators = age_sex_generators
        self.comorbidity_data = comorbidity_data

    def populate(
        self, area_name: str, ethnicity=True, comorbidity=True,
    ) -> Population:
        """
        Generate a population for a given area. Age, sex and number of residents
        are all based on census data for that area.

        Parameters
        ----------
        area_name
            The name of an area a population should be generated for

        Returns
        -------
        A population of people
        """
        people = []
        age_and_sex_generator = self.age_sex_generators[area_name]
        if comorbidity:
            comorbidity_generator = ComorbidityGenerator(self.comorbidity_data)
        for _ in range(age_and_sex_generator.n_residents):
            if ethnicity:
                ethnicity_value = age_and_sex_generator.ethnicity()
            else:
                ethnicity_value = None
            person = Person.from_attributes(
                age=age_and_sex_generator.age(),
                sex=age_and_sex_generator.sex(),
                ethnicity=ethnicity_value,
            )
            if comorbidity:
                person.comorbidity = comorbidity_generator.get_comorbidity(person)
            people.append(person)  # add person to population
        return Population(people=people)

    @classmethod
    def for_geography(
        cls,
        geography: Geography,
        data_path: str = default_data_path,
        config: Optional[dict] = None,
    ) -> "Demography":
        """
        Initializes demography from an existing geography.

        Parameters
        ----------
        geography
            an instance of the geography class
        """
        if not geography.areas:
            raise DemographyError("Empty geography!")
        area_names = [area.name for area in geography.areas]
        return cls.for_areas(area_names, data_path, config)

    @classmethod
    def for_zone(
        cls,
        filter_key: Dict[str, list],
        data_path: str = default_data_path,
        areas_maps_path: str = default_areas_map_path,
        config: Optional[dict] = None,
    ) -> "Demography":
        """
        Initializes a geography for a specific list of zones. The zones are
        specified by the filter_dict dictionary where the key denotes the
        kind of zone, and the value is a list with the different zone names. 
        
        Example
        -------
            filter_key = {"region" : "North East"}
            filter_key = {"super_area" : ["EXXXX", "EYYYY"]}
        """
        if len(filter_key.keys()) > 1:
            raise NotImplementedError("Only one type of area filtering is supported.")
        geo_hierarchy = pd.read_csv(areas_maps_path)
        zone_type, zone_list = filter_key.popitem()
        area_names = geo_hierarchy[geo_hierarchy[zone_type].isin(zone_list)]["area"]
        if not area_names.size:
            raise DemographyError("Region returned empty area list.")
        return cls.for_areas(area_names, data_path, config)

    @classmethod
    def for_areas(
        cls,
        area_names: List[str],
        data_path: str = default_data_path,
        config: Optional[dict] = None,
        config_path: str = default_config_path,
    ) -> "Demography":
        """
        Load data from files and construct classes capable of generating demographic
        data for individuals in the population.

        Parameters
        ----------
        area_names
            List of areas for which to create a demographic generator.
        data_path
            The path to the data directory
        config
            Optional configuration. At the moment this just gives an asymptomatic
            ratio.

        Returns
        -------
            A demography representing the super area
        """
        area_names = area_names
        age_structure_path = data_path / "age_structure_single_year.csv"
        female_fraction_path = data_path / "female_ratios_per_age_bin.csv"
        ethnicity_structure_path = data_path / "ethnicity_structure.csv"
        m_comorbidity_path = data_path / "uk_male_comorbidities.csv"
        f_comorbidity_path = data_path / "uk_female_comorbidities.csv"
        age_sex_generators = _load_age_and_sex_generators(
            age_structure_path,
            female_fraction_path,
            ethnicity_structure_path,
            area_names,
        )
        comorbidity_data = load_comorbidity_data(m_comorbidity_path, f_comorbidity_path)
        return Demography(
            age_sex_generators=age_sex_generators,
            area_names=area_names,
            comorbidity_data=comorbidity_data,
        )


def _load_age_and_sex_generators(
    age_structure_path: str,
    female_ratios_path: str,
    ethnicity_structure_path: str,
    area_names: List[str],
) -> Dict[str, AgeSexGenerator]:
    """
    A dictionary mapping area identifiers to a generator of age, sex, ethnicity.

    Returns
    -------
    ethnicity_structure_path
        File containing ethnicity nr. per Area.
        This approach chosen based on:
        Davis, J. A., & Smith, T. W. (1999); Chicago: National Opinion Research Center
    """
    age_structure_df = pd.read_csv(age_structure_path, index_col=0)
    age_structure_df = age_structure_df.loc[area_names]
    age_structure_df.sort_index(inplace=True)

    female_ratios_df = pd.read_csv(female_ratios_path, index_col=0)
    female_ratios_df = female_ratios_df.loc[area_names]
    female_ratios_df.sort_index(inplace=True)

    ethnicity_structure_df = pd.read_csv(
        ethnicity_structure_path, index_col=[0, 1]
    )  # pd MultiIndex!!!
    ethnicity_structure_df = ethnicity_structure_df.loc[pd.IndexSlice[area_names]]
    ethnicity_structure_df.sort_index(level=0, inplace=True)
    ## "sort" is required as .loc slicing a multi_index df doesn't work as expected --
    ## it preserves original order, and ignoring "repeat slices".
    # TODO fix this to use proper complete indexing.

    ret = {}
    for (
        (_, age_structure),
        (index, female_ratios),
        (_, ethnicity_df),
    ) in zip(
        age_structure_df.iterrows(),
        female_ratios_df.iterrows(),
        ethnicity_structure_df.groupby(level=0),
    ):
        ethnicity_structure = [ethnicity_df[col].values for col in ethnicity_df.columns]
        ret[index] = AgeSexGenerator(
            age_structure.values,
            female_ratios.index.values,
            female_ratios.values,
            ethnicity_df.columns,
            ethnicity_df.index.get_level_values(1),
            ethnicity_structure,
        )

    return ret


def load_comorbidity_data(m_comorbidity_path=None, f_comorbidity_path=None):
    if m_comorbidity_path is not None and f_comorbidity_path is not None:
        male_co = pd.read_csv(m_comorbidity_path)
        female_co = pd.read_csv(f_comorbidity_path)

        male_co = male_co.set_index("comorbidity")
        female_co = female_co.set_index("comorbidity")

        for column in male_co.columns:
            m_nc = male_co[column].loc["no_condition"]
            m_norm_1 = 1 - m_nc
            m_norm_2 = np.sum(male_co[column]) - m_nc

            f_nc = female_co[column].loc["no_condition"]
            f_norm_1 = 1 - f_nc
            f_norm_2 = np.sum(female_co[column]) - f_nc

            for idx in list(male_co.index)[:-1]:
                male_co[column].loc[idx] = (
                    male_co[column].loc[idx] / m_norm_2 * m_norm_1
                )
                female_co[column].loc[idx] = (
                    female_co[column].loc[idx] / f_norm_2 * f_norm_1
                )

        return [male_co, female_co]

    else:
        return None


class ComorbidityGenerator:
    def __init__(self, comorbidity_data):
        self.male_comorbidities_probabilities = np.array(
            comorbidity_data[0].values.T, dtype=np.float64
        )
        self.female_comorbidities_probabilities = np.array(
            comorbidity_data[1].values.T, dtype=np.float64
        )
        self.ages = np.array(comorbidity_data[0].columns).astype(int)
        self.comorbidities = np.array(comorbidity_data[0].index).astype(str)
        self.comorbidities_idx = np.arange(0, len(self.comorbidities))

    def _get_age_index(self, person):
        column_index = 0
        for idx, i in enumerate(self.ages):
            if person.age <= i:
                break
            else:
                column_index = idx
        if column_index != 0:
            column_index += 1
        return column_index

    def get_comorbidity(self, person):
        age_index = self._get_age_index(person)
        if person.sex == "m":
            comorbidity_idx = random_choice_numba(
                self.comorbidities_idx, self.male_comorbidities_probabilities[age_index]
            )
        else:
            comorbidity_idx = random_choice_numba(
                self.comorbidities_idx,
                self.female_comorbidities_probabilities[age_index],
            )
        return self.comorbidities[comorbidity_idx]


def generate_comorbidity(person, comorbidity_data):
    if comorbidity_data is not None:

        male_co = comorbidity_data[0]
        female_co = comorbidity_data[1]
        ages = np.array(male_co.columns).astype(int)

        column_index = 0
        for idx, i in enumerate(ages):
            if person.age <= i:
                break
            else:
                column_index = idx
        if column_index != 0:
            column_index += 1

        if person.sex == "m":
            return random_choice_numba(
                male_co.index.values.astype(str),
                male_co[male_co.columns[column_index]].values,
            )

        elif person.sex == "f":
            return random_choice_numba(
                female_co.index.values.astype(str),
                female_co[female_co.columns[column_index]].values,
            )
    else:
        return None


def load_age_and_sex_generators_for_bins(
    age_sex_bins_filename: str, by="super_area"
) -> Dict[str, AgeSexGenerator]:
    """
    """
    data = pd.read_csv(age_sex_bins_filename, index_col=0)
    area_names = data[by].values
    men = data.loc[:, data.columns.str.contains("M")].copy()
    rename_dict = {}
    for column in men.columns:
        rename_dict[column] = column.split(" ")[1]
    men.rename(columns=rename_dict, inplace=True)
    women = data.loc[:, data.columns.str.contains("F")].copy()
    rename_dict = {}
    for column in women.columns:
        rename_dict[column] = column.split(" ")[1]
    women.rename(columns=rename_dict, inplace=True)
    ret = {}
    i = 0
    for (area_name, men_row), (_, women_row) in zip(men.iterrows(), women.iterrows()):
        generator = AgeSexGenerator.from_age_sex_bins(
            men_row.to_dict(), women_row.to_dict()
        )
        ret[area_names[i]] = generator
        i += 1
    return ret
