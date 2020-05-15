import logging
from itertools import count
from typing import List, Dict, Tuple, Optional

import pandas as pd

from june import paths
from june.demography.person import Person


default_hierarchy_filename = (
        paths.data_path
        / "processed/geographical_data/oa_msoa_region.csv"
)
default_area_coord_filename = (
        paths.data_path
        / "processed/geographical_data/oa_coordinates.csv"
)
default_superarea_coord_filename = (
        paths.data_path
        / "processed/geographical_data/msoa_coordinates.csv"
)
default_logging_config_filename = (
        paths.configs_path / "config_world_creation_logger.yaml"
)

logger = logging.getLogger(__name__)


class Area:
    """
    Fine geographical resolution.
    """

    __slots__ = (
        "households",
        "people",
        "id",
        "name",
        "coordinates",
        "super_area",
        "carehome",
    )
    _id = count()

    def __init__(
            self,
            name: str,
            super_area: "SuperArea",
            coordinates: Tuple[float, float],
    ):
        """
        Coordinate is given in the format Y, X where X is longitude and Y is latitude.
        """
        self.id = next(self._id)
        self.name = name
        self.coordinates = coordinates
        self.super_area = super_area
        self.people = set()

    def add(self, person: Person):
        self.people.add(person)
        person.area = self

    def populate(self, demography):
        for person in demography.populate(
                self.name
        ):
            self.add(person)


class Areas:
    __slots__ = "members", "super_area"

    def __init__(self, areas: List[Area], super_area=None):
        self.members = areas
        self.super_area = super_area

    def __len__(self):
        return len(self.members)

    def __iter__(self):
        return iter(self.members)


class SuperArea:
    """
    Coarse geographical resolution.
    """

    __slots__ = "id", "name", "coordinates", "workers", "areas", "companies"
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
        self.areas = areas
        self.workers = list()
        self.companies = list()

    def add_worker(self, person: Person):
        self.workers.append(person)
        person.work_super_area = self


class SuperAreas:
    def __init__(self, super_areas: List[SuperArea]):
        self.members = super_areas

    def __len__(self):
        return len(self.members)

    def __iter__(self):
        return iter(self.members)

    def __getitem__(self, item):
        return self.members[item]


class Geography:
    def __init__(
            self,
            hierarchy: pd.DataFrame,
            area_coordinates: pd.DataFrame,
            super_area_coordinates: pd.DataFrame,
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
        self.create_geographical_units(
            hierarchy, area_coordinates, super_area_coordinates
        )

    @staticmethod
    def _create_area(row, super_area):
        area = Area(name=row.name, coordinates=row.values, super_area=super_area)
        return area

    def _create_areas(
            self, area_coords: pd.DataFrame, super_area: pd.DataFrame
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
        # and apply doesnt support the axis parameter.
        try:
            areas = area_coords.apply(
                lambda row: self._create_area(row, super_area), axis=1, result_type='expand'
            ).values
        except TypeError:
            return [self._create_area(area_coords, super_area)]
        return areas

    def create_geographical_units(
            self,
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
        for superarea_name, row in super_area_coordinates.iterrows():
            super_area = SuperArea(areas=None, name=superarea_name, coordinates=row.values)
            areas_df = area_coordinates.loc[hierarchy.loc[row.name, "oa"]]
            areas_list = self._create_areas(areas_df, super_area)
            super_area.areas = areas_list
            total_areas_list += list(areas_list)
            super_areas_list.append(super_area)

        self.areas = Areas(total_areas_list)
        self.super_areas = SuperAreas(super_areas_list)
        logger.info(
            f"There are {len(self.areas)} areas and "
            + f"{len(self.super_areas)} super_areas in the world."
        )

    @classmethod
    def from_file(
            cls,
            filter_key: Optional[Dict[str, list]] = None,
            hierarchy_filename: str = default_hierarchy_filename,
            area_coordinates_filename: str = default_area_coord_filename,
            super_area_coordinates_filename: str = default_superarea_coord_filename,
            logging_config_filename: str = default_logging_config_filename,
    ) -> "Geography":
        """
        Load data from files and construct classes capable of generating
        hierarchical structure of geographical areas.

        Example usage
        -------------
            ```
            geography = Geography.from_file(filter_key={"region" : "North East"})
            geography = Geography.from_file(filter_key={"msoa" : ["E02005728"]})
            ```
        Parameters
        ----------
        filter_key
            Filter out geo-units which should enter the world.
            At the moment this can only be one of [oa, msoa, region]
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
        areas_coord = pd.read_csv(area_coordinates_filename, index_col=0)
        super_areas_coord = pd.read_csv(super_area_coordinates_filename, index_col=0)

        if filter_key is not None:
            geo_hierarchy = _filtering(geo_hierarchy, filter_key)

        areas_coord = areas_coord.loc[geo_hierarchy["oa"]].loc[:, ["Y", "X"]]
        super_areas_coord = super_areas_coord.loc[
                                geo_hierarchy["msoa"]
                            ].loc[:, ["Y", "X"]].drop_duplicates()
        geo_hierarchy.set_index("msoa", inplace=True)
        return cls(geo_hierarchy, areas_coord, super_areas_coord)


def _filtering(data: pd.DataFrame, filter_key: Dict[str, list], ) -> pd.DataFrame:
    """
    Filter DataFrame for given geo-unit and it's listed names
    """
    return data[
        data[list(filter_key.keys())[0]].isin(list(filter_key.values())[0]).values
    ]
