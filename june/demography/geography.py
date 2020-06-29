import logging, os
from pathlib import Path
from itertools import count, chain
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree

from june import paths
from june.demography.person import Person

default_hierarchy_filename = (
    paths.data_path / "input/geography/area_super_area_region.csv"
)
default_area_coord_filename = paths.data_path / "input/geography/area_coordinates.csv"
default_superarea_coord_filename = (
    paths.data_path / "input/geography/super_area_coordinates.csv"
)
default_logging_config_filename = (
    paths.configs_path / "config_world_creation_logger.yaml"
)

logger = logging.getLogger(__name__)

earth_radius = 6371  # km


class GeographyError(BaseException):
    pass


class Area:
    """
    Fine geographical resolution.
    """

    __slots__ = (
        "people",
        "id",
        "name",
        "coordinates",
        "super_area",
        "care_home",
        "schools",
        "households",
    )
    _id = count()

    def __init__(
        self, name: str, super_area: "SuperArea", coordinates: Tuple[float, float],
    ):
        """
        Coordinate is given in the format [Y, X] where X is longitude and Y is latitude.
        """
        self.id = next(self._id)
        self.name = name
        self.care_home = None
        self.coordinates = coordinates
        self.super_area = super_area
        self.people = list()
        self.schools = list()
        self.households = list()

    def add(self, person: Person):
        self.people.append(person)
        person.area = self

    def populate(self, demography):
        for person in demography.populate(self.name):
            self.add(person)


class Areas:
    __slots__ = "members", "super_area", "ball_tree"

    def __init__(self, areas: List[Area], super_area=None, ball_tree: bool = True):
        self.members = areas
        self.super_area = super_area
        if ball_tree:
            self.ball_tree = self.construct_ball_tree()
        else:
            self.ball_tree = None

    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self.members)

    def __getitem__(self, index):
        return self.members[index]

    def construct_ball_tree(self):
        coordinates = np.array([np.deg2rad(area.coordinates) for area in self])
        ball_tree = BallTree(coordinates)
        return ball_tree

    def get_closest_areas(self, coordinates, k=1, return_distance=False):
        coordinates = np.array(coordinates)
        if self.ball_tree is None:
            raise GeographyError("Areas initialized without a BallTree")
        if coordinates.shape == (2,):
            coordinates = coordinates.reshape(1, -1)
        if return_distance:
            distances, indcs = self.ball_tree.query(
                np.deg2rad(coordinates), return_distance=return_distance, k=k
            )
            areas = [self[idx] for idx in indcs[:, 0]]
            return areas, distances[:, 0] * earth_radius
        else:
            indcs = self.ball_tree.query(
                np.deg2rad(coordinates), return_distance=return_distance, k=k
            )
            areas = [self[idx] for idx in indcs[:, 0]]
            return areas


class SuperArea:
    """
    Coarse geographical resolution.
    """

    __slots__ = (
        "id",
        "name",
        "coordinates",
        "workers",
        "areas",
        "companies",
        "groceries",
    )
    _id = count()

    def __init__(
        self,
        name: str = None,
        areas: List[Area] = None,
        coordinates: Tuple[float, float] = None,
    ):
        self.id = next(self._id)
        self.name = name
        self.coordinates = coordinates
        self.areas = areas or list()
        self.workers = list()
        self.companies = list()
        self.groceries = list()

    def add_worker(self, person: Person):
        self.workers.append(person)
        person.work_super_area = self

    @property
    def people(self):
        return list(chain(*[area.people for area in self.areas]))


class SuperAreas:
    __slots__ = "members", "ball_tree"

    def __init__(self, super_areas: List[SuperArea], ball_tree: bool = True):
        """
        Group to aggregate SuperArea objects.

        Parameters
        ----------
        super_areas
            list of super areas
        ball_tree
            whether to construct a NN tree for the super areas
        """
        self.members = super_areas
        if ball_tree:
            self.ball_tree = self.construct_ball_tree()
        else:
            self.ball_tree = None

    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self.members)

    def __getitem__(self, index):
        return self.members[index]

    def construct_ball_tree(self):
        coordinates = np.array(
            [np.deg2rad(super_area.coordinates) for super_area in self]
        )
        ball_tree = BallTree(coordinates)
        return ball_tree

    def get_closest_super_areas(self, coordinates, k=1, return_distance=False):
        coordinates = np.array(coordinates)
        if self.ball_tree is None:
            raise GeographyError("Areas initialized without a BallTree")
        if coordinates.shape == (2,):
            coordinates = coordinates.reshape(1, -1)
        if return_distance:
            distances, indcs = self.ball_tree.query(
                np.deg2rad(coordinates),
                return_distance=return_distance,
                k=k,
                sort_results=True,
            )
            indcs = list(chain(*indcs))
            super_areas = [self[idx] for idx in indcs]
            distances = np.array(list(chain(*distances)))
            return super_areas, distances * earth_radius
        else:
            indcs = self.ball_tree.query(
                np.deg2rad(coordinates),
                return_distance=return_distance,
                k=k,
                sort_results=True,
            )
            indcs = list(chain(*indcs))
            super_areas = [self[idx] for idx in indcs]
            return super_areas


class Geography:
    def __init__(
        self, areas: List[Area], super_areas: List[SuperArea],
    ):
        """
        Generate hierachical devision of geography.

        Parameters
        ----------
        hierarchy
            The different geographical division units from which the
            hierachical structure will be constructed.
        area_coordinates

        Note: It would be nice to find a better way to handle coordinates.
        """
        self.areas = areas
        self.super_areas = super_areas
        # possible buildings
        self.households = None
        self.schools = None
        self.hospitals = None
        self.companies = None
        self.care_homes = None
        self.pubs = None
        self.cinemas = None
        self.groceries = None
        self.cemeteries = None
        self.universities = None

    @classmethod
    def _create_areas(
        cls, area_coords: pd.DataFrame, super_area: pd.DataFrame
    ) -> List[Area]:
        """
        Applies the _create_area function throught the area_coords dataframe.
        If area_coords is a series object, then it does not use the apply()
        function as it does not support the axis=1 parameter.

        Parameters
        ----------
        area_coords
            pandas Dataframe with the area name as index and the coordinates
            X, Y where X is longitude and Y is latitude.
        """
        # if a single area is given, then area_coords is a series
        # and we cannot do iterrows()
        if isinstance(area_coords, pd.Series):
            areas = [Area(area_coords.name, super_area, area_coords.values)]
        else:
            areas = []
            for name, coordinates in area_coords.iterrows():
                areas.append(
                    Area(
                        name,
                        super_area,
                        coordinates=np.array(
                            [coordinates.latitude, coordinates.longitude]
                        ),
                    )
                )
        return areas

    @classmethod
    def create_geographical_units(
        cls,
        hierarchy: pd.DataFrame,
        area_coordinates: pd.DataFrame,
        super_area_coordinates: pd.DataFrame,
    ):
        """
        Create geo-graph of the used geographical units.

        Note: This function looks a bit more complicated than need be,
        but it was created with a eye on the future.
        """
        total_areas_list = []
        super_areas_list = []
        for super_area_name, row in super_area_coordinates.iterrows():
            super_area = SuperArea(
                areas=None,
                name=super_area_name,
                coordinates=np.array([row.latitude, row.longitude]),
            )
            areas_df = area_coordinates.loc[hierarchy.loc[super_area_name, "area"]]
            areas_list = cls._create_areas(areas_df, super_area)
            super_area.areas = areas_list
            total_areas_list += list(areas_list)
            super_areas_list.append(super_area)
        areas = Areas(total_areas_list)
        super_areas = SuperAreas(super_areas_list)
        logger.info(
            f"There are {len(areas)} areas and "
            + f"{len(super_areas)} super_areas in the world."
        )
        return areas, super_areas

    @classmethod
    def from_file(
        cls,
        filter_key: Optional[Dict[str, list]] = None,
        hierarchy_filename: str = default_hierarchy_filename,
        area_coordinates_filename: str = default_area_coord_filename,
        super_area_coordinates_filename: str = default_superarea_coord_filename,
    ) -> "Geography":
        """
        Load data from files and construct classes capable of generating
        hierarchical structure of geographical areas.

        Example usage
        -------------
            ```
            geography = Geography.from_file(filter_key={"region" : "North East"})
            geography = Geography.from_file(filter_key={"super_area" : ["E02005728"]})
            ```
        Parameters
        ----------
        filter_key
            Filter out geo-units which should enter the world.
            At the moment this can only be one of [area, super_area, region]
        hierarchy_filename
            Pandas df file containing the relationships between the different
            geographical units.
        area_coordinates_filename:
            coordinates of the area units
        super_area_coordinates_filename
            coordinates of the super area units
        logging_config_filename
            file path of the logger configuration
        """
        geo_hierarchy = pd.read_csv(hierarchy_filename)
        areas_coord = pd.read_csv(area_coordinates_filename)
        super_areas_coord = pd.read_csv(super_area_coordinates_filename)

        if filter_key is not None:
            geo_hierarchy = _filtering(geo_hierarchy, filter_key)

        areas_coord = areas_coord.loc[areas_coord.area.isin(geo_hierarchy.area)]
        super_areas_coord = super_areas_coord.loc[
            super_areas_coord.super_area.isin(geo_hierarchy.super_area)
        ].drop_duplicates()
        areas_coord.set_index("area", inplace=True)
        super_areas_coord.set_index("super_area", inplace=True)
        geo_hierarchy.set_index("super_area", inplace=True)
        areas, super_areas = cls.create_geographical_units(
            geo_hierarchy, areas_coord, super_areas_coord
        )
        return cls(areas, super_areas)


def _filtering(data: pd.DataFrame, filter_key: Dict[str, list],) -> pd.DataFrame:
    """
    Filter DataFrame for given geo-unit and it's listed names
    """
    return data[
        data[list(filter_key.keys())[0]].isin(list(filter_key.values())[0]).values
    ]
