from typing import List, Tuple, Optional
import numpy as np
import collections
from enum import IntEnum
from sklearn.neighbors import BallTree
from june.groups import Group, Supergroup
from june.demography import Person


class LearningCenter(Group):
    class SubgroupType(IntEnum):
        teachers = 0
        students = 1

    def __init__(
        self, coordinates: Tuple[float, float], n_pupils_max: int,
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
        self, learning_centers: List[LearningCenter], learning_centers_tree: Optional[BallTree] = None
    ):
        super().__init__()
        self.members = learning_centers
        self.learning_centers_tree = learning_centers_tree
        self.has_shifts = True

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
        return BallTree(np.deg2rad(schools_coordinates), metric="haversine")

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
