from typing import List, Tuple, Optional
import numpy as np
import yaml
import collections
from enum import IntEnum
from sklearn.neighbors import BallTree
from camps import paths
from june.groups import Group, Supergroup
from june.demography import Person

default_learning_centers_coordinates_path = (
    paths.camp_data_path / "input/learning_centers/learning_centers.csv"
)
default_config_path = paths.camp_configs_path / "defaults/groups/learning_center.yaml"


class LearningCenter(Group):
    class SubgroupType(IntEnum):
        teachers = 0
        students = 1

    def __init__(
        self, coordinates: Tuple[float, float], n_pupils_max: int = 35,
    ):
        super().__init__()
        self.coordinates = coordinates
        self.n_pupils_max = n_pupils_max
        self.active_shift = 0
        self.has_shifts = True
        self.ids_per_shift = collections.defaultdict(list)

    def add(self, person: Person, shift: int, subgroup_type=SubgroupType.students):
        super().add(
            person=person, activity="primary_activity", subgroup_type=subgroup_type
        )
        self.ids_per_shift[shift].append(person.id)

    @classmethod
    def for_areas(
        cls,
        areas: "Areas",
        coordinates_path: str = default_learning_centers_coordinates_path,
        max_distance_to_area=5,
        max_size=np.inf,
    ):
        learning_centers_df = pd.read_csv(coordinates_path)
        coordinates = learning_centers_df.loc[:, ["latitude", "longitude"]].values
        return cls.from_coordinates(
            coordinates, max_size, areas, max_distance_to_area=max_distance_to_area,
        )

    @classmethod
    def for_geography(
        cls,
        geography,
        coordinates_path: str = default_learning_centers_coordinates_path,
        max_distance_to_area=5,
        max_size=np.inf,
    ):
        return cls.for_areas(
            areas=geography.areas,
            coordinates_path=coordinates - path,
            max_size=max_size,
            max_distance_to_area=max_distance_to_area,
        )

    @classmethod
    def from_coordinates(
        cls,
        coordinates: List[np.array],
        max_size=np.inf,
        areas: Optional["Areas"] = None,
        max_distance_to_area=5,
        **kwargs
    ):
        if areas is not None:
            _, distances = areas.get_closest_areas(
                coordinates, k=1, return_distance=True
            )
            distances_close = np.where(distances < max_distance_to_area)
            coordinates = coordinates[distances_close]
        learning_centers = list()
        for coord in coordinates:
            lc = LearningCenter(coordinates=coordinates)
            learning_centers.append(lc)
        return cls(learning_centers, **kwargs)

    @property
    def n_pupils(self):
        return len(self.students)

    @property
    def n_teachers(self):
        return len(self.teachers)

    @property
    def teachers(self):
        return self.subgroups[self.SubgroupType.teachers]

    @property
    def students(self):
        return self.subgroups[self.SubgroupType.students]


class LearningCenters(Supergroup):
    def __init__(
        self,
        learning_centers: List[LearningCenter],
        learning_centers_tree: bool = True,
    ):
        super().__init__()
        self.members = learning_centers
        if learning_centers_tree:
            coordinates = np.vstack([np.array(lc.coordinates) for lc in self.members]).T
            print(coordinates)
            self.learning_centers_tree = self._create_learning_center_tree(coordinates)
        self.has_shifts = True

    @classmethod
    def from_config(
        cls, learning_centers: "LearningCenters", config_path: str = default_config_path
    ):
        with open(config_path) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(learning_centers, **config)

    @staticmethod
    def _create_learning_center_tree(
        learning_centers_coordinates: np.ndarray,
    ) -> BallTree:
        """

        Parameters
        ----------
        learning centers coordinates: 
            array with coordinates

        Returns
        -------
        Tree to query nearby learning centers 

        """
        return BallTree(np.deg2rad(learning_centers_coordinates), metric="haversine")

    def get_closest(self, coordinates: Tuple[float, float], k: int) -> int:
        """
        Get the k-th closest learning center to a given coordinate

        Parameters
        ----------
        coordinates: 
            latitude and longitude
        k:
            k-th neighbour

        Returns
        -------
        ID of the k-th closest learning center

        """
        coordinates_rad = np.deg2rad(coordinates).reshape(1, -1)
        k = min(k, len(list(self.learning_centers_tree.data)))
        distances, neighbours = self.learning_centers_tree.query(
            coordinates_rad, k=k, sort_results=True,
        )
        return neighbours[0]

    def activate_next_shift(self, n_shifts):
        for learning_center in self.members:
            learning_center.active_shift += 1
            if learning_center.active_shift == n_shifts:
                learning_center.active_shift = 0
