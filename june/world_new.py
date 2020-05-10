import os
import pickle
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import numpy as np
import yaml
from tqdm.auto import tqdm  # for a fancy progress bar

from june.geography import Geography
from june.demography import Demography, People
from june.logger_creation import logger

logger = logging.getLogger(__name__)


class World:
    """
    This Class creates the world that will later be simulated.
    The world will be stored in pickle, but a better option needs to be found.
    
    Note: BoxMode = Demography +- Sociology - Geography
    """

    def __init__(
        self,
        geography: Geography,
        demography: Demography,
    ):
        self.areas = geography.areas
        self.super_areas = geography.super_areas
        print("populating the world's geography with the specified demography...")
        for area in self.areas:
            population = demography.population_for_area(area.name)
            for person in population:
                area.add(person)

    @classmethod
    def from_geography(cls, geography: Geography):
        """
        Initializes the world given a geometry. The demography is calculated
        with the default settings for that geography.
        """
        demography = Demography.for_geography(geography)
        return cls(geography, demography)

