import csv
import logging
import logging.config
from pathlib import Path
from random import randint
from typing import List, Dict, Optional

import numpy as np

from june.geography.areas import Area
from june.geography.super_areas import SuperArea

default_data_path = Path(__file__).parent.parent.parent.parent / \
        "data/census_data/area_code_translations"

default_logging_config_filename = Path(__file__).parent.parent.parent.parent / \
        "configs/config_world_creation_logger.yaml"

class Area:
    def __init__(
            self,
    ):
        """
        Each fine Area should know to which SuperArea it belongs.
        Parameters
        ----------
        """

class SuperArea:
    def __init__(
            self,
            super_area: str,
            area: List[Area],
    ):
        """
        A collection of any geographical divisions (e.g. area/OA and super_area/MSOA).
        A Zones is: a portion of the surface of a sphere included between
                    two parallel planes.

        Behaves mostly like a list but also has the name of the area attached.

        Parameters
        ----------
        """
        self.super_area = super_area
        self.area = area

    def __len__(self):
        return len(self.area)

    def __iter__(self):
        return iter(self.area)


class Geography:
    def __init__(
            self,
            hierarchy: pd.DataFrame,
    ):
        """
        Generate hierachical devision of geography.

        Parameters
        ----------
        geo_hierarchy
            The different geographical division units from which the
            hierachical structure will be constructed.
        """
        self.hierarchy = hierarchy


    def aggregate(self):
        """
        Sort fin granular geographical units into their coarse granular units.
        """

    def find_hierarchy(self):
        """
        Find which geographical units are coarse and fine granular.

        Parameters
        ----------
        area
            An area within the super-area represented by this demography

        Returns
        -------
        A population of people
        """
        all_zones = self.hierarchy.columns.values
        self.hierarchy = self.hierarchy.groupby(all_zones).size()
        hierarchy = [
            [zone, len(self.hierarchy[zone].values)]
            for zone in self.hierarchy.columns.values]
        ]

    @classmethod
    def from_file(
            cls,
            data_path: str = default_data_path,
            logging_config_filename: str = default_logging_config_filename,
    ) -> "Geography":
        """
        Load data from files and construct classes capable of generating
        hierarchical structure of geographical areas.

        Parameters
        ----------
        data_path
            The path to the data directory

        Returns
        -------
        """
        #TODO this file is missing option to filter for Region etc.
        geo_hierarchy_file = f"{data_path}/areas_mapping.csv"

        usecols = [0, 1, 3]
        column_names = ["PCD", "OA", "MSOA"]
        geo_hierarchy = pd.read_csv(
            geo_hierarchy_file,
            names=column_names,
            usecols=usecols,
        )

        _logger(logging_config_filename)

        return Geography(geo_hierarchy)


def _logger(self, config_file: str = None):
    """
    Create logger to make debugging easier
    """
    #TODO this function can be made global to be used by any file
    if config_file is None:
        config_file = self.configs_dir + "config_create_world.yaml"
    if os.path.isfile(config_file):
        with open(config_file, 'rt') as f:
            #log_config = yaml.safe_load(f.read())
            configs = yaml.load(f, Loader=yaml.FullLoader)
        logging.config.dictConfig(log_config)
    else:
        print("The provided logging config file does not exist.")
        log_file = os.path.join(self.output_dir, "world_creation.log")
        logging.basicConfig(
            filename=log_file, level=logging.DEBUG
        )
