import csv
from pathlib import Path
from random import randint
from typing import List, Dict, Optional

import numpy as np

from june.geography import Geography
from june.demography.health_index import HealthIndex
from june.demography.person import Person

default_data_path = Path(__file__).parent.parent.parent.parent / "data"

MALE_INDEX = 1
FEMALE_INDEX = 2


def parse_age(age_string: str) -> int:
    """
    Parse an age string, dealing with the XXX convention
    """
    if age_string == "XXX":
        return 100
    return int(age_string)


class AgeGenerator:
    def __init__(
            self,
            lower: int,
            upper: Optional[int] = None,
    ):
        """
        Encapsulates an age range and can be called to randomly generate
        ages within that range.
        
        Parameters
        ----------
        lower
            The lower bound of the range
        upper
            The upper bound of the range. If this is None then the range is
            a specific age
        """
        self.lower = lower
        self.upper = upper or lower

    def __call__(self) -> int:
        """
        Randomly select an age from the range, inclusively.
        """
        return randint(
            self.lower,
            self.upper
        )

    @classmethod
    def from_range_string(
            cls,
            string: str
    ) -> "AgeGenerator":
        """
        Parse an age range string.

        If it is just a single number the range is that number.
        If it is two numbers divided by a dash then the range is
        between those two numbers.
        If it includes an XXX that is translated to be 100.

        Parameters
        ----------
        string
            A string representation of an age range, e.g. 0-4

        Returns
        -------
        An object that can randomly generate ages in that range.
        """
        return AgeGenerator(
            *map(
                parse_age,
                string.split(
                    "-"
                )
            )
        )


class Population:
    def __init__(
            self, area: str,
            people: List[Person]
    ):
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
            super_area: str,
            geography: "Geography",
            residents_map: Dict[str, int],
            sex_generators: Dict[str, "WeightedGenerator"],
            age_generators: Dict[str, "WeightedGenerator"],
            health_index: HealthIndex
    ):
        """
        Generate populations for a given area based on census data.

        Parameters
        ----------
        super_area
            The wider region for which the demography is represented
        residents_map
            A dictionary mapping area identifiers to the number of residents
        sex_generators
            A dictionary mapping area identifiers to functions that generate
            male or female classifications for individuals
        age_generators
            A dictionary mapping area identifiers to functions that generate
            age ranges for individuals
        health_index
            A class used to look up health indices for people based on their
            age
        """
        self.super_area = super_area
        self.residents_map = residents_map
        self.sex_generators = sex_generators
        self.age_generators = age_generators
        self.health_index = health_index

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
        people = list()
        for _, sex, age_range in zip(
                range(
                    self.residents_map[area]
                ),
                self.sex_generators[area],
                self.age_generators[area]
        ):
            age = age_range()
            health_index = self.health_index.get_index_for_age(age)
            people.append(
                Person(
                    sex=sex,
                    age=age_range(),
                    health_index=health_index
                )
            )
        return Population(
            area=area,
            people=people
        )

    @classmethod
    def for_super_area(
            cls,
            super_area,
            data_path: str = default_data_path,
            config: Optional[dict] = None
    ) -> "Demography":
        """
        Load data from files and construct classes capable of generating demographic
        data for individuals in the population.

        Parameters
        ----------
        super_area
            An identifier for a larger geographical area, e.g. NorthEast
        data_path
            The path to the data directory
        config
            Optional configuration. At the moment this just gives an asymptomatic
            ratio.

        Returns
        -------
        A demography representing the super area
        """
        health_index = HealthIndex(
            config=config
        )

        output_area_path = f"{data_path}/processed/census_data/output_area/{super_area}"
        age_structure_path = f"{output_area_path}/age_structure.csv"
        sex_path = f"{output_area_path}/sex.csv"
        residents_path = f"{output_area_path}/residents.csv"

        residents_map = _load_residents_map(
            residents_path
        )
        sex_generators = _load_sex_generators(
            sex_path
        )
        age_generators = _load_age_generators(
            age_structure_path
        )

        return Demography(
            super_area,
            residents_map=residents_map,
            sex_generators=sex_generators,
            age_generators=age_generators,
            health_index=health_index
        )


def _load_age_generators(
        age_structure_path: str
) -> Dict[str, "WeightedGenerator"]:
    """
    A dictionary mapping area identifiers to functions that generate
    age ranges for individuals
    """
    with open(age_structure_path) as f:
        reader = csv.reader(f)
        age_generators = map(
            AgeGenerator.from_range_string,
            next(reader)[1:]
        )
        return {
            row[0]: WeightedGenerator(
                *[
                    (int(weight), age_generator)
                    for weight, age_generator
                    in zip(row[1:], age_generators)
                ]
            )
            for row in reader
        }


def _load_residents_map(
        residents_path: str
) -> Dict[str, int]:
    """
    A dictionary mapping area identifiers to the number of residents
    """
    with open(residents_path) as f:
        reader = csv.reader(f)
        next(reader)
        return {
            row[0]: int(row[1])
            for row in reader
        }


def _load_sex_generators(
        sex_path: str
) -> Dict[str, "WeightedGenerator"]:
    """
    A dictionary mapping area identifiers to functions that generate
    male or female classifications for individuals
    """
    with open(sex_path) as f:
        reader = csv.reader(f)
        headers = next(reader)
        if not ("m" in headers[MALE_INDEX] and "f" in headers[FEMALE_INDEX]):
            raise AssertionError(
                f"sex dataset at {sex_path} does not match expected structure"
            )
        return {
            row[0]: WeightedGenerator(
                (int(row[MALE_INDEX]), "m"),
                (int(row[FEMALE_INDEX]), "f")
            )
            for row in reader
        }


class WeightedGenerator:
    def __init__(self, *possibilities):
        """
        Takes a list of tuples where the first value is a non-normalised
        weight and the second value an associated possible outcome of
        weighted variable selection.

        Parameters
        ----------
        possibilities
            [(probability, outcome)]
        """
        self.possibilities = possibilities

    @property
    def values(self) -> List[int]:
        """
        The possible outcomes
        """
        return [
            possibility[1]
            for possibility
            in self.possibilities
        ]

    @property
    def weights(self) -> List[int]:
        """
        The associated, non-normalised weights
        """
        return [
            possibility[0]
            for possibility
            in self.possibilities
        ]

    @property
    def normalised_weights(self) -> List[float]:
        """
        The normalised weights
        """
        weights = self.weights
        return [
            weight / sum(weights)
            for weight
            in weights
        ]

    def __iter__(self):
        return self

    def __next__(self):
        return self()

    def __call__(self):
        """
        Weighted-randomly pick an outcome
        """
        return np.random.choice(
            self.values,
            p=self.normalised_weights
        )
