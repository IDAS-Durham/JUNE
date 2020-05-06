import csv
from pathlib import Path
from typing import List, Dict

from covid.groups.people.person import Person

default_data_path = Path(__file__).parent.parent.parent.parent / "data"


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

    def create_person(self):
        person = Person(
            age=age_random,
            nomis_bin=nomis_bin,
            sex=sex_random,
            health_index=health_index
        )

    def random_sex(self):
        return self.area.sex_rv.rvs(
            size=self.area.n_residents
        )


class Demography:
    def __init__(
            self,
            super_area: str,
            residents_map: Dict[str, int]
    ):
        self.super_area = super_area
        self.residents_map = residents_map

    def population_for_area(self, area: str):
        people = list()
        for _ in range(
                self.residents_map[area]
        ):
            people.append(
                Person()
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
        residents_path = f"{output_area_path}/residents.csv"

        with open(residents_path) as f:
            reader = csv.reader(f)
            next(reader)
            residents_map = {
                row[0]: int(row[1])
                for row in reader
            }

        return Demography(
            super_area,
            residents_map=residents_map
        )
