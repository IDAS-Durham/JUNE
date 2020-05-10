import os
import pickle
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import numpy as np
import yaml
import pickle
from tqdm.auto import tqdm  # for a fancy progress bar

from june.geography import Geography
from june.demography import Demography, People
from june.logger_creation import logger
from june.distributors import SchoolDistributor, HospitalDistributor, HouseholdDistributor

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
        include_households: bool = True,
    ):
        """
        Initializes a world given a geography and a demography. For now, households are
        a special group because they require a mix of both groups (we need to fix
        this later). 

        Parameters
        ----------
        geography
            an instance of the Geography class specifying the "board"
        demography
            an instance of the Demography class with generators to generate people with 
            certain demographic attributes
        include_households
            whether to include households in the world or not (defualt = True)
        """
        self.areas = geography.areas
        self.super_areas = geography.super_areas
        print("populating the world's geography with the specified demography...")
        population = demography.populate(self.areas)
        WorkerDistributor(population)
        if include_households:
            print("Creating and populating households...")
            household_distributor = HouseholdDistributor.from_file()
            self.households = household_distributor.distribute_people_and_households_to_areas(
                self.areas
            )
        if hasattr(geography, "schools"):
            self.schools = geography.schools
            school_distributor = SchoolDistributor(geography.schools)
            school_distributor.distribute_kids_to_school(self.areas)

    
    @classmethod
    def from_geography(cls, geography: Geography):
        """
        Initializes the world given a geometry. The demography is calculated
        with the default settings for that geography.
        """
        demography = Demography.for_geography(geography)
        return cls(geography, demography)

    def to_pickle(self, save_path):
        with open(save_path, "wb") as f:
            pickle.dump(self, f, 4)

if __name__ == "__main__":
    geography = Geography.from_file(filter_key={"oa" : ["E00088544"]})
    world = World.from_geography(geography)



