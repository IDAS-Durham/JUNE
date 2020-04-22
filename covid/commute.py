import csv
from pathlib import Path
from typing import List, Tuple

import numpy as np
import yaml

default_config_filename = Path(
    __file__
).parent.parent / "configs/commute.yaml"


class RegionalGenerator:
    def __init__(
            self,
            code: str,
            weighted_modes: List[
                Tuple[int, "ModeOfTransport"]
            ]
    ):
        self.code = code
        self.weighted_modes = weighted_modes

    @property
    def total(self):
        return sum(
            mode[0]
            for mode
            in self.weighted_modes
        )

    @property
    def modes(self):
        return [
            mode[1]
            for mode
            in self.weighted_modes
        ]

    @property
    def weights(self):
        return [
            mode[0] / self.total
            for mode
            in self.weighted_modes
        ]

    def weighted_random_choice(self):
        return np.random.choice(
            self.modes,
            p=self.weights
        )

    def __repr__(self):
        return f"<{self.__class__.__name__} {self}>"

    def __str__(self):
        return self.code


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

    def index(self, headers):
        for i, header in enumerate(headers):
            if self.description in header:
                return i
        raise AssertionError(
            f"{self} not found in headers {headers}"
        )

    def __eq__(self, other):
        if isinstance(other, str):
            return self.description == other
        if isinstance(other, ModeOfTransport):
            return self.description == other.description
        return super().__eq__(other)

    def __hash__(self):
        return hash(self.description)

    def __str__(self):
        return self.description

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.description}>"

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
                weighted_modes = list()
                for mode in modes_of_transport:
                    weighted_modes.append((
                        int(row[
                                mode.index(headers)
                            ]),
                        mode
                    ))
                code = row[code_column]
                regional_generators.append(
                    RegionalGenerator(
                        code=code,
                        weighted_modes=weighted_modes
                    )
                )
        return CommuteGenerator(
            regional_generators
        )
