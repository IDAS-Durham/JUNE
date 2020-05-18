import logging
from itertools import count, chain
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import pandas as pd
import numpy as np
import h5py

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
    )
    _id = count()

    def __init__(
        self, name: str, super_area: "SuperArea", coordinates: Tuple[float, float],
    ):
        """
        Coordinate is given in the format Y, X where X is longitude and Y is latitude.
        """
        self.id = next(self._id)
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


class Areas:
    __slots__ = "members", "super_area"

    def __init__(self, areas: List[Area], super_area=None):
        self.members = areas
        self.super_area = super_area

    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self.members)

    def __getitem__(self, index):
        return self.members[index]

    def erase_people_from_geographical_unit(self):
        """
        Sets all attributes in self.references_to_people to None for all groups.
        Erases all people from subgroups.
        """
        for geo_unit in self:
            geo_unit.people.clear()


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

    @property
    def people(self):
        return list(chain(*[area.people for area in self.areas]))


class SuperAreas:
    __slots__ = "members"

    def __init__(self, super_areas: List[SuperArea]):
        self.members = super_areas

    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self.members)

    def __getitem__(self, index):
        return self.members[index]

    def erase_people_from_geographical_unit(self):
        """
        Sets all attributes in self.references_to_people to None for all groups.
        Erases all people from subgroups.
        """
        for geo_unit in self:
            geo_unit.people.clear()
            geo_unit.workers.clear()
            geo_unit.areas.clear()
            # geo_unit.companies.clear()


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
                areas.append(Area(name, super_area, coordinates.values))
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
        for superarea_name, row in super_area_coordinates.iterrows():
            super_area = SuperArea(
                areas=None, name=superarea_name, coordinates=row.values
            )
            areas_df = area_coordinates.loc[hierarchy.loc[row.name, "oa"]]
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
        areas, super_areas = cls.create_geographical_units(
            geo_hierarchy, areas_coord, super_areas_coord
        )
        return cls(areas, super_areas)

    def to_hdf5(self, file_path: str):
        n_areas = len(self.areas)
        area_ids = []
        area_names = []
        area_super_areas = []
        area_coordinates = []
        n_super_areas = len(self.super_areas)
        super_area_ids = []
        super_area_names = []
        super_area_coordinates = []

        for area in self.areas:
            area_ids.append(area.id)
            area_super_areas.append(area.super_area.id)
            area_names.append(area.name.encode("ascii", "ignore"))
            area_coordinates.append(np.array(area.coordinates, dtype=np.float))

        for super_area in self.super_areas:
            super_area_ids.append(super_area.id)
            super_area_names.append(super_area.name.encode("ascii", "ignore"))
            super_area_coordinates.append(np.array(super_area.coordinates))

        area_ids = np.array(area_ids, dtype=np.int)
        area_names = np.array(area_names, dtype="S10")
        area_super_areas = np.array(area_super_areas, dtype=np.int)
        area_coordinates = np.array(area_coordinates, dtype=np.float)
        super_area_ids = np.array(super_area_ids, dtype=np.int)
        super_area_names = np.array(super_area_names, dtype="S10")
        super_area_coordinates = np.array(super_area_coordinates, dtype=np.float)

        with h5py.File(file_path, "w") as f:
            people_dset = f.create_group("geography")
            people_dset.attrs["n_areas"] = n_areas
            people_dset.attrs["n_super_areas"] = n_super_areas
            people_dset.create_dataset("area_id", data=area_ids)
            people_dset.create_dataset("area_name", data=area_names)
            people_dset.create_dataset("area_super_area", data=area_super_areas)
            people_dset.create_dataset("area_coordinates", data=area_coordinates)
            people_dset.create_dataset("super_area_id", data=super_area_ids)
            people_dset.create_dataset("super_area_name", data=super_area_names)
            people_dset.create_dataset(
                "super_area_coordinates", data=super_area_coordinates
            )

    @classmethod
    def from_hdf5(cls, file_path: str):
        with h5py.File(file_path, "r") as f:
            geography = f["geography"]
            chunk_size = 50000
            n_areas = geography.attrs["n_areas"]
            area_list = list()
            n_super_areas = geography.attrs["n_super_areas"]
            # areas
            n_chunks = int(np.ceil(n_areas / chunk_size))
            for chunk in range(n_chunks):
                idx1 = chunk * chunk_size
                idx2 = min((chunk + 1) * chunk_size, n_areas)
                ids = geography["area_id"][idx1:idx2]
                names = geography["area_name"][idx1:idx2]
                super_areas = geography["area_super_area"][idx1:idx2]
                area_coordinates = geography["area_coordinates"][idx1:idx2]
                for k in range(idx2 - idx1):
                    area = Area(names[k].decode(), super_areas[k], area_coordinates[k])
                    area.id = ids[k]
                    area_list.append(area)
            # super areas
            super_area_list = list()
            n_chunks = int(np.ceil(n_super_areas / chunk_size))
            for chunk in range(n_chunks):
                idx1 = chunk * chunk_size
                idx2 = min((chunk + 1) * chunk_size, n_super_areas)
                ids = geography["super_area_id"][idx1:idx2]
                names = geography["super_area_name"][idx1:idx2]
                super_area_coordinates = geography["super_area_coordinates"][idx1:idx2]
                for k in range(idx2 - idx1):
                    print(k)
                    print(names)
                    print(super_area_coordinates)
                    super_area = SuperArea(names[k].decode(), None, super_area_coordinates[k])
                    super_area.id = ids[k]
                    super_area_list.append(super_area)

        return cls(area_list, super_area_list)


def _filtering(data: pd.DataFrame, filter_key: Dict[str, list],) -> pd.DataFrame:
    """
    Filter DataFrame for given geo-unit and it's listed names
    """
    return data[
        data[list(filter_key.keys())[0]].isin(list(filter_key.values())[0]).values
    ]
