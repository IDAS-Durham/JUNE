import csv
from pathlib import Path
from random import randint
from typing import List, Dict

import numpy as np

from covid.groups.people.person import Person

default_data_path = Path(__file__).parent.parent.parent.parent / "data"

MALE_INDEX = 1
FEMALE_INDEX = 2


def parse_age(age_string):
    if age_string == "XXX":
        return 100
    return int(age_string)


class AgeGenerator:
    def __init__(self, lower, upper=None):
        self.lower = lower
        self.upper = upper or lower

    def __call__(self):
        return randint(
            self.lower,
            self.upper
        )

    @classmethod
    def from_range_string(cls, string):
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
        self.area = area
        self.people = people

    def __len__(self):
        return len(self.people)

    def __iter__(self):
        return iter(self.people)

    # def create_person(self):
    #     person = Person(
    #         age=age_random,
    #         nomis_bin=nomis_bin,
    #         sex=sex_random,
    #         health_index=health_index
    #     )


class Demography:
    def __init__(
            self,
            super_area: str,
            residents_map: Dict[str, int],
            sex_generators: Dict[str, "WeightedGenerator"],
            age_generators: Dict[str, "WeightedGenerator"]
    ):
        self.super_area = super_area
        self.residents_map = residents_map
        self.sex_generators = sex_generators
        self.age_generators = age_generators

    def population_for_area(self, area: str):
        people = list()
        for _, sex, age_range in zip(
                range(
                    self.residents_map[area]
                ),
                self.sex_generators[area],
                self.age_generators[area]
        ):
            people.append(
                Person(
                    sex=sex,
                    age=age_range()
                )
            )
        return Population(
            area=area,
            people=people
        )

    @classmethod
    def from_super_area(
            cls,
            super_area,
            data_path: str = default_data_path
    ):
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
            age_generators=age_generators
        )


def _load_age_generators(
        age_structure_path
):
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
):
    with open(residents_path) as f:
        reader = csv.reader(f)
        next(reader)
        return {
            row[0]: int(row[1])
            for row in reader
        }


def _load_sex_generators(
        sex_path: str
):
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
        self.possibilities = possibilities

    @property
    def values(self):
        return [
            possibility[1]
            for possibility
            in self.possibilities
        ]

    @property
    def weights(self):
        return [
            possibility[0]
            for possibility
            in self.possibilities
        ]

    @property
    def normalised_weights(self):
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
        return np.random.choice(
            self.values,
            p=self.normalised_weights
        )
