import os
import csv
from pathlib import Path
from random import randint
from typing import List, Dict, Optional

import pandas as pd
import numpy as np

# from june.demography.health_index import HealthIndex
from june.geography import Geography
from june.demography import Person

default_data_path = (
    Path(os.path.abspath(__file__)).parent.parent.parent
    / "data/processed/census_data/output_area/EnglandWales"
)

default_areas_map_path = (
    Path(os.path.abspath(__file__)).parent.parent.parent
    / "data/processed/geographical_data/oa_msoa_region.csv"
)


class DemographyError(BaseException):
    pass


class AgeSexGenerator:
    def __init__(self, age_counts: list, sex_bins: list, female_fractions: list):
        """
        age_counts is an array where the index in the array indicates the age,
        and the value indicates the number of counts in that age.
        sex_bins are the lower edges of each sex bin where we have a fraction of females from
        census data, and female_fractions are those fractions.
        Example:
            age_counts = [1, 2, 3] means 1 person of age 0, 2 people of age 1 and 3 people of age 2.
            sex_bins = [1, 3] defines two bins: (0,1) and (3, infinity)
            female_fractions = [0.3, 0.5] means that between the ages 0 and 1 there are 30% females,
                                          and there are 50% females in the bin 3+ years
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

    def age(self) -> int:
        try:
            return next(self.age_iterator)
        except StopIteration:
            raise DemographyError("No more people living here!")

    def sex(self) -> str:
        try:
            return next(self.sex_iterator)
        except StopIteration:
            raise DemographyError("No more people living here!")


class Population:
    def __init__(self, area: str, people: List[Person]):
        """
        A population of people.

        Behaves mostly like a list but also has the name of the area attached.

        Parameters
        ----------
        area
            The name of some geographical area
        people
            A list of people generated to match census data for that area
        """
        self.area = area
        self.people = people

    def __len__(self):
        return len(self.people)

    def __iter__(self):
        return iter(self.people)


class Demography:
    def __init__(
        self,
        area_names,
        age_sex_generators: Dict[str, AgeSexGenerator],
        health_index_generator: "HealthIndex" = None,
        ethnicity_generators: Dict[str, "EthnicityGenerator"] = None,
        economic_index_generators: Dict[str, "EconomicIndexGenerator"] = None,
    ):
        """
        Tool to generate population for a certain geographical regin.

        Parameters
        ----------
        age_sex_generators
            A dictionary mapping area identifiers to functions that generate
            age and sex for individuals.
        health_index_generator
            A class used to look up health indices for people based on their
            age
        ethnicity_generators
            A dictionary mapping area identifiers to functions that allocate
            individuals to ethnic groups.
       economic_index_generators: 
            A dictionary mapping area identifiers to functions that allocate
            individuals to socioeconomic classes.
        """
        self.area_names = area_names
        self.age_sex_generators = age_sex_generators
        self.health_index_generator = health_index_generator
        # not implemented yet:
        self.ethnicity_generators = ethnicity_generators
        self.economic_index_generators = economic_index_generators

    def population_for_area(self, area: str) -> Population:
        """
        Generate a population for a given area. Age, sex and number of residents
        are all based on census data for that area.

        Parameters
        ----------
        area
            An area within the super-area represented by this demography

        Returns
        -------
        A population of people
        """
        # TODO: this could be make faster with map()
        people = list()
        age_and_sex_generator = self.age_sex_generators[area]
        for _ in range(age_and_sex_generator.n_residents):
            person = Person(
                age=age_and_sex_generator.age(), sex=age_and_sex_generator.sex()
            )
            people.append(person)
        return Population(area=area, people=people)

    @classmethod
    def for_areas(
        cls,
        area_names: List[str],
        data_path: str = default_data_path,
        config: Optional[dict] = None,
    ) -> "Demography":
        """
        Load data from files and construct classes capable of generating demographic
        data for individuals in the population.

        Parameters
        ----------
        area_names
            list of areas for which to create populations
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
        age_sex_generators = _load_age_and_sex_generators(
            age_structure_path, female_fraction_path, area_names
        )
        return Demography(age_sex_generators=age_sex_generators, area_names=area_names)

    @classmethod
    def for_zone(
        cls,
        filter_key: Dict[str, list],
        data_path: str = default_data_path,
        areas_maps_path: str = default_areas_map_path,
        config: Optional[dict] = None,
    ) -> "Demography":
        """
        Initializes a geography for a specific list of zones. The zones are specified by the filter_dict dictionary
        where the key denotes the kind of zone, and the value is a list with the different zone names. 
        Example:
            filter_key = {"region" : "North East"}
            filter_key = {"msoa" : ["EXXXX", "EYYYY"]}
        """
        if len(filter_key.keys()) > 1:
            raise NotImplementedError("Only one type of area filtering is supported.")
        geo_hierarchy = pd.read_csv(areas_maps_path)
        zone_type, zone_list = filter_key.popitem()
        area_names = geo_hierarchy[geo_hierarchy[zone_type].isin(zone_list)]["oa"]
        if len(area_names) == 0:
            raise DemographyError("Region returned empty area list.")
        return cls.for_areas(area_names, data_path, config)

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
        area_names = [area.name for area in geography.areas]
        if len(area_names) == 0:
            raise DemographyError("Empty geography!")
        return cls.for_areas(area_names, data_path, config)


def _load_age_and_sex_generators(
    age_structure_path: str, female_ratios_path: str, area_names: List[str]
):
    """
    A dictionary mapping area identifiers to a generator of age and sex.
    """
    age_structure_df = pd.read_csv(age_structure_path, index_col=0)
    age_structure_df = age_structure_df.loc[area_names]
    female_ratios_df = pd.read_csv(female_ratios_path, index_col=0)
    female_ratios_df = female_ratios_df.loc[area_names]
    ret = {}
    for (_, age_structre), (index, female_ratios) in zip(
        age_structure_df.iterrows(), female_ratios_df.iterrows()
    ):
        ret[index] = AgeSexGenerator(
            age_structre.values, female_ratios.index.values, female_ratios.values
        )
    return ret


if __name__ == "__main__":
    from time import time
    import resource

    def using(point=""):
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return """%s: usertime=%s systime=%s mem=%s mb
               """ % (
            point,
            usage[0],
            usage[1],
            usage[2] / 1024.0,
        )

    t1 = time()
    print(using("before"))
    demography = Demography.for_regions(["North East"])
    for area in demography.area_names:
        demography.population_for_area(area)
    t2 = time()
    print(using("after"))
    print(f"Took {t2-t1} seconds to populate the UK.")
