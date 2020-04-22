import csv
from typing import List


class RegionalGenerator:
    def __init__(self, code: str):
        self.code = code


class CommuteGenerator:
    def __init__(
            self,
            regional_generators: List[RegionalGenerator]
    ):
        self.regional_generators = regional_generators

    @classmethod
    def from_file(cls, filename: str) -> "CommuteGenerator":
        regional_generators = list()
        with open(filename) as f:
            reader = csv.reader(f)
            headers = next(reader)
            code_column = headers.index("geography code")
            for row in reader:
                code = row[code_column]
                regional_generators.append(
                    RegionalGenerator(
                        code=code
                    )
                )
        return CommuteGenerator(
            regional_generators
        )
