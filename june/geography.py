import logging
from itertools import count, chain
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import pandas as pd
import numpy as np

from june import paths
from june.demography.person import Person


default_hierarchy_filename = (
    paths.data_path / "processed/geographical_data/oa_msoa_region.csv"
)
default_area_coord_filename = (
    paths.data_path / "processed/geographical_data/oa_coordinates.csv"
)
default_superarea_coord_filename = (
    paths.data_path / "processed/geographical_data/msoa_coordinates.csv"
)
default_logging_config_filename = (
    paths.configs_path / "config_world_creation_logger.yaml"
)

logger = logging.getLogger(__name__)


class GeographicalUnit:
    """
    Template for a geography group.
    """

    __id_generators = defaultdict(count)

    @classmethod
    def _next_id(cls) -> int:
        """
        Iterate an id for this class. Each group class has its own id iterator
        starting at 0
        """
        return next(cls.__id_generators[cls])

    def __init__(self):
        self.id = self._next_id()

    @classmethod
    def from_file(cls):
        raise NotImplementedError(
            "From file initialization not available for this supergroup."
        )

    def erase_people_from_geographical_unit(self):
        """
        Sets all attributes in self.references_to_people to None for all groups.
        Erases all people from subgroups.
        """
        for geo_unit in self:
            geo_unit.people.clear()


class Area(GeographicalUnit):
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
        "care_home",
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
        super().__init__()
        self.name = name
        self.coordinates = coordinates
        self.super_area = super_area
        self.people = list()

    def add(self, person: Person):
        self.people.append(person)
        person.area = self

    def populate(self, demography):
        for person in demography.populate(self.name):
            self.add(person)


class Areas(GeographicalUnit):
    __slots__ = "members", "super_area"

    def __init__(self, areas: List[Area], super_area=None):
        super().__init__()
        self.members = areas
        self.super_area = super_area

    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self.members)

    def __getitem__(self, index):
        return self.members[index]


class SuperArea(GeographicalUnit):
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
        super().__init__()
        self.id = next(self._id)
        self.name = name
        self.coordinates = coordinates
        self.areas = areas
        self.workers = list()
        self.companies = list()

    def add_worker(self, person: Person):
        self.workers.append(person)
        person.work_super_area = self

    @property
    def people(self):
        return list(chain(*[area.people for area in self.areas]))


class SuperAreas(GeographicalUnit):
    __slots__ = "members"

    def __init__(self, super_areas: List[SuperArea]):
        super().__init__()
        self.members = super_areas
    
    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self.members)

    def __getitem__(self, index):
        return self.members[index]


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
    def _create_area(name, coordinates, super_area):
        area = Area(name=name, coordinates=coordinates, super_area=super_area)
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
        # and we cannot do iterrows()
        if isinstance(area_coords, pd.Series):
            areas = [Area(area_coords.name, super_area, area_coords.values)]
        else:
            areas = []
            for name, coordinates in area_coords.iterrows():
                areas.append(Area(name, super_area, coordinates.values))

        #try:
        #    areas = list(
        #        map(
        #            lambda row: self._create_area(row[0], row[1].values, super_area),
        #            area_coords.iterrows(),
        #        )
        #    )
        #except AttributeError:  # it's a series
        #    return [self._create_area(area_coords.name, area_coords.values, super_area)]
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
            super_area = SuperArea(
                areas=None, name=superarea_name, coordinates=row.values
            )
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
        super_areas_coord = (
            super_areas_coord.loc[geo_hierarchy["msoa"]]
            .loc[:, ["Y", "X"]]
            .drop_duplicates()
        )
        geo_hierarchy.set_index("msoa", inplace=True)
        return cls(geo_hierarchy, areas_coord, super_areas_coord)


def _filtering(data: pd.DataFrame, filter_key: Dict[str, list],) -> pd.DataFrame:
    """
    Filter DataFrame for given geo-unit and it's listed names
    """
    return data[
        data[list(filter_key.keys())[0]].isin(list(filter_key.values())[0]).values
    ]
