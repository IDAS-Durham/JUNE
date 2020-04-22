import csv
from pathlib import Path
from typing import List

import yaml

default_config_filename = Path(
    __file__
).parent.parent / "configs/commute.yaml"


class RegionalGenerator:
    def __init__(self, code: str):
        self.code = code


class ModeOfTransport:
    __all = dict()

    def __new__(cls, description):
        if description not in ModeOfTransport.__all:
            ModeOfTransport.__all[
                description
            ] = super().__new__(cls)
        return ModeOfTransport.__all[
            description
        ]

    def __init__(
            self,
            description
    ):
        self.description = description

    def __eq__(self, other):
        if isinstance(other, str):
            return self.description == other
        if isinstance(other, ModeOfTransport):
            return self.description == other.description
        return super().__eq__(other)

    def __hash__(self):
        return hash(self.description)

    @classmethod
    def load_from_file(
            cls,
            config_filename=default_config_filename
    ):
        with open(config_filename) as f:
            configs = yaml.load(f)
        return [
            ModeOfTransport(
                config["description"]
            )
            for config in configs
        ]


class CommuteGenerator:
    def __init__(
            self,
            regional_generators: List[RegionalGenerator]
    ):
        self.regional_generators = regional_generators

    @classmethod
    def from_file(
            cls,
            filename: str,
            config_filename: str = default_config_filename
    ) -> "CommuteGenerator":
        regional_generators = list()
        with open(filename) as f:
            reader = csv.reader(f)
            headers = next(reader)
            code_column = headers.index("geography code")
            modes_of_transport = ModeOfTransport.load_from_file(
                config_filename
            )
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
