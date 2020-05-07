import csv
import logging
from pathlib import Path
from random import randint
from typing import List, Dict, Optional

import numpy as np

from june.geography.areas import Area
from june.geography.super_areas import SuperArea
from june import get_creation_logger

default_data_path = Path(__file__).parent.parent.parent.parent / \
        "data/census_data/area_code_translations"

default_logging_config_filename = Path(__file__).parent.parent.parent.parent / \
        "configs/config_world_creation_logger.yaml"

get_creation_logger(default_logging_config_filename)
logger = logging.getLogger(__name__)


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


    @classmethod
    def from_file(
            cls,
            data_path: str = default_data_path,
            filter_key: Optional[Dict[str, list]] = None,
            logging_config_filename: str = default_logging_config_filename,
    ) -> "Geography":
        """
        Load data from files and construct classes capable of generating
        hierarchical structure of geographical areas.

        Parameters
        ----------
        data_path
            The path to the data directory
        filter_key
            Filter out geo-units which should enter the world.
            At the moment this can only be one of [PCD, OA, MSOA]

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
        
        if filter_key not None:
            geo_hierarchy = _filtering(geo_hierarchy, filter_key)

        geo_hierarchy = _sorting(geo_hierarchy)

        return Geography(geo_hierarchy)


def _filtering(data: pd.DataFrame, filter_key: Optional[Dict[str, list]] = None):
    """
    Filter DataFrame for given geo-unit and it's listed names
    """
    return data[ data[filter_key["unit"]].isin(filter_key["names"]) ]


def _sorting(self, hierarchy: pd.DataFrame):
    """
    Find the order for available geographical units from coarse
    to fine granular.
    
    Returns
    -------
    A DataFrame with the first colume the most coarse and the last
    column the finest division of geography.
    """
    nr_unique_units = [len(dic[unit].unique())
        for unit in dic.columns.values
    ]
    idx = np.argsort(np.array(nr_unique_units))
    return hierarchy[hierarchy.columns.values[idx]]
