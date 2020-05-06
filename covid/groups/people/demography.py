from typing import List

from covid.groups.people.person import Person
from pathlib import Path


default_data_path = Path(__file__).parent.parent.parent.parent / "data"


class Population:
    def __init__(
            self, area: str,
            people: List[Person]
    ):
        self.area = area
        self.people = people

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
            super_area: str
    ):
        self.super_area = super_area

    def population_for_area(self, area: str):
        pass

    @classmethod
    def from_super_area(
            cls,
            super_area,
            data_path: str=default_data_path
    ):
        age_structure_path = f"{data_path}/census_data/output_area/{super_area}/age_structure.csv"
        return Demography(
            super_area
        )
