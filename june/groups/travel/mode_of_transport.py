import csv
from typing import List, Tuple, Dict

import numpy as np
import yaml

from june import paths
from june.utils import random_choice_numba

default_config_filename = paths.configs_path / "defaults/groups/travel/mode_of_transport.yaml"

default_commute_file = paths.data_path / "input/travel/mode_of_transport_ew.csv"


class ModeOfTransport:
    __all = {}
    __slots__ = "description", "is_public"

    def __new__(
            cls,
            description,
            is_public=False
    ):
        if description not in ModeOfTransport.__all:
            ModeOfTransport.__all[
                description
            ] = super().__new__(cls)
        return ModeOfTransport.__all[
            description
        ]

    def __init__(
            self,
            description: str,
            is_public: bool = False
    ):
        """
        Create a ModeOfTransport from its description.

        Only one instance of each mode of transport exists with instances being
        retrieved from the __all dictionary.

        Parameters
        ----------
        description
            e.g. "Bus, minibus or coach"
        is_public
            True if this is public transport, for example a bus.
        """
        self.description = description
        self.is_public = is_public

    @property
    def is_private(self) -> bool:
        """
        True if this is private transport, for example a car.
        """
        return not self.is_public

    @classmethod
    def with_description(
            cls,
            description: str
    ) -> "ModeOfTransport":
        """
        Retrieve a mode of transport by its description.

        Parameters
        ----------
        description
            A description, e.g. 'Bus, minibus or coach'

        Returns
        -------
        The corresponding ModeOfTransport instance
        """
        return ModeOfTransport.__all[
            description
        ]

    def index(self, headers: List[str]) -> int:
        """
        Determine the column index of this mode of transport.

        The first header that contains this mode of transport's description
        is counted.

        Parameters
        ----------
        headers
            A list of headers from a CSV file.

        Returns
        -------
        The column index corresponding to this mode of transport.

        Raises
        ------
        An assertion error if no such header is found.
        """
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
        return f"<{self.__class__.__name__} {self}>"

    def __getnewargs__(self):
        return self.description, self.is_public

    @classmethod
    def load_from_file(
            cls,
            config_filename=default_config_filename
    ) -> List["ModeOfTransport"]:
        """
        Load all of the modes of transport from commute.yaml.

        Modes of transport are globally unique. That is, even if the function
        is called twice identical mode of transport objects are returned.

        Parameters
        ----------
        config_filename
            The path to the mode of transport yaml configuration

        Returns
        -------
        A list of modes of transport
        """
        with open(config_filename) as f:
            configs = yaml.load(f, Loader=yaml.FullLoader)
        return [
            ModeOfTransport(
                **config
            )
            for config in configs
        ]


class RegionalGenerator:
    def __init__(
            self,
            area: str,
            weighted_modes: List[
                Tuple[int, "ModeOfTransport"]
            ]
    ):
        """
        Randomly generate modes of transport, weighted by usage, for
        one particular region.

        Parameters
        ----------
        area
            A unique identifier for a Output region
        weighted_modes
            A list of tuples comprising the number of people using a mode
            of a transport and a representation of that mode of transport
        """
        self.area = area
        self.weighted_modes = weighted_modes
        self.total = self._get_total()
        self.modes = self._get_modes()
        self.weights = self._get_weights()
        self.modes_idx = np.arange(0, len(self.modes))

    def _get_total(self) -> int:
        """
        The sum of the numbers of people using each mode of transport
        """
        return sum(
            mode[0]
            for mode
            in self.weighted_modes
        )

    def _get_modes(self) -> List["ModeOfTransport"]:
        """
        A list of modes of transport
        """
        return [
            mode[1]
            for mode
            in self.weighted_modes
        ]

    def _get_weights(self) -> List[float]:
        """
        The normalised weights for each mode of transport.
        """
        return np.array([
            mode[0] / self.total
            for mode
            in self.weighted_modes
        ])

    def weighted_random_choice(self) -> "ModeOfTransport":
        """
        Randomly choose a mode of transport, weighted by usage in this region.
        """
        idx = random_choice_numba(self.modes_idx, self.weights)
        return self.modes[idx]

    def __repr__(self):
        return f"<{self.__class__.__name__} {self}>"

    def __str__(self):
        return self.area


class ModeOfTransportGenerator:
    def __init__(
            self,
            regional_generators: Dict[str, RegionalGenerator]
    ):
        """
        Generate a mode of transport that a person uses in their commute.

        Modes of transport are chosen randomly, weighted by the numbers taken
        from census data for each given Output area.

        Parameters
        ----------
        regional_generators
            A dictionary mapping Geography areas to objects that randomly
            generate modes of transport
        """
        self.regional_generators = regional_generators

    def regional_gen_from_area(self, area: str) -> RegionalGenerator:
        """
        Get a regional generator for an Area identified
        by its output output area, e.g. E00062207

        Parameters
        ----------
        super_area
            A code for an super_area

        Returns
        -------
        An object that weighted-randomly selects modes of transport for the region.
        """
        return self.regional_generators[
            area
        ]

    @classmethod
    def from_file(
            cls,
            filename: str = default_commute_file,
            config_filename: str = default_config_filename
    ) -> "ModeOfTransportGenerator":
        """
        Parse configuration describing each included mode of transport
        along with census data describing the weightings for modes of
        transport in each output area.

        Parameters
        ----------
        filename
            The path to the commute.csv file.
            This contains data on the number of people using each mode
            of transport.
        config_filename
            The path to the commute.yaml file

        Returns
        -------
        An object used to generate commutes
        """
        regional_generators = {}
        with open(filename) as f:
            reader = csv.reader(f)
            headers = next(reader)
            area_column = headers.index("geography code")
            modes_of_transport = ModeOfTransport.load_from_file(
                config_filename
            )
            for row in reader:
                weighted_modes = []
                for mode in modes_of_transport:
                    weighted_modes.append((
                        int(row[
                                mode.index(headers)
                            ]),
                        mode
                    ))
                area = row[area_column]
                regional_generators[area] = RegionalGenerator(
                    area=area,
                    weighted_modes=weighted_modes
                )

        return ModeOfTransportGenerator(
            regional_generators
        )
