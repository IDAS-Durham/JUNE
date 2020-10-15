import numpy as np
from typing import List
from itertools import count, chain
from sklearn.cluster import KMeans
from sklearn.neighbors import KDTree
from collections import defaultdict
import pandas as pd
import logging
import h5py

logger = logging.getLogger("domain")

from june.demography import Population
from june.geography import SuperArea
from june.hdf5_savers import generate_domain_from_hdf5
from june import paths

# default_super_area_shapes_path = paths.data_path / "plotting/super_area_boundaries"
default_super_area_centroids = (
    paths.data_path / "input/geography/super_area_centroids.csv"
)


class Domain:
    """
    The idea is that the world is divided in domains, which are just collections of super areas with
    people living/working/doing leisure in them.
    
    If we think as domains as sets, then world is the union of all domains, and each domain can have
    a non-zero intersection with other domains (some people can work and live in different domains).
    
    Domains are sent to MPI core to perfom calculation, and communcation between the processes is
    required to transfer the infection status of people.
    """

    _id = count()

    def __init__(self, id: int = None):
        if id is None:
            self.id = next(self._id)
        self.id = id

    def __iter__(self):
        return iter(self.super_areas)

    @property
    def box_mode(self):
        return False

    @classmethod
    def from_hdf5(
        cls, domain_id, super_areas_to_domain_dict: dict, hdf5_file_path: str,
    ):
        domain = generate_domain_from_hdf5(
            domain_id=domain_id,
            super_areas_to_domain_dict=super_areas_to_domain_dict,
            file_path=hdf5_file_path,
        )
        domain.id = domain_id
        return domain


class DomainSplitter:
    """
    Class used to split the world into ``n`` domains containing an equal number
    of super areas continuous to each other.
    """

    def __init__(
        self,
        number_of_domains: int,
        world_path: str,
        super_area_centroids: List[List[float]] = None,
    ):
        """
        Parameters
        ----------
        super_areas
            a list of super area names
        number_of_domains
            how many domains to split for
        super_area_boundaries_path
            path to a shape file containing the shapes of super areas
        super_area_key
            column name of the shape file that contains the super area identifiers.
        """
        with h5py.File(world_path, "r") as f:
            self.super_area_names = [
                super_area.decode() for super_area in f["geography"]["super_area_name"]
            ]
        self.number_of_domains = number_of_domains
        self.super_area_centroids = super_area_centroids
        if self.super_area_centroids is None:
            self.super_area_centroids = pd.read_csv(
                default_super_area_centroids, index_col=0
            )
        if self.super_area_names is None:
            self.super_area_names = self.super_area_centroids.index.values
        self.super_area_centroids = self.super_area_centroids.loc[self.super_area_names]
        self.score_per_super_area = self.get_scores_per_super_area(world_path)
        self.average_score_per_domain = (
            sum(self.score_per_super_area.values()) / number_of_domains
        )
        self.super_areas_sorted = self._sort_super_areas_by_score()

    def get_scores_per_super_area(self, world_path):
        people_weight = 3
        workers_weight = 1
        commute_weight = 3
        ret = defaultdict(float)
        with h5py.File(world_path, "r") as f:
            geography_dset = f["geography"]
            super_area_names = geography_dset["super_area_name"][:]
            super_area_ids = geography_dset["super_area_id"][:]
            super_area_names = [name.decode() for name in super_area_names]
            super_area_id_to_name = {
                key: value for key, value in zip(super_area_ids, super_area_names)
            }
            stations_dset = f["stations"]
            for station_super_area, station_commuters in zip(
                stations_dset["super_area"], stations_dset["commuters"]
            ):
                ret[super_area_id_to_name[station_super_area]] += commute_weight * len(
                    station_commuters
                )
            for super_area_name, n_people, n_workers in zip(
                geography_dset["super_area_name"],
                geography_dset["super_area_n_people"],
                geography_dset["super_area_n_workers"],
            ):
                ret[super_area_name.decode()] += (
                    people_weight * n_people + workers_weight * n_workers
                )
        return ret

    def _sort_super_areas_by_score(self):
        super_area_scores = [
            self.score_per_super_area[super_area]
            for super_area in self.super_area_names
        ]
        return [
            self.super_area_names[idx] for idx in np.argsort(super_area_scores)[::-1]
        ]

    def get_score_per_domain(self, super_areas_per_domain):
        ret = defaultdict(float)
        for key, value in super_areas_per_domain.items():
            score = 0
            for sa in value:
                score += self.score_per_super_area[sa]
            ret[key] = score
        return ret

    def _get_kmeans_centroids(self):
        X = np.array(
            list(zip(self.super_area_centroids["X"], self.super_area_centroids["Y"]))
        )
        kmeans = KMeans(n_clusters=self.number_of_domains).fit(X)
        cluster_centers = kmeans.cluster_centers_
        return cluster_centers

    def _initialise_kdtree(self, data):
        kdtree = KDTree(data)
        return kdtree

    def _get_closest_centroid_id(self, kdtree, coordinates):
        closest_centroid_ids = kdtree.query(coordinates.reshape(1, -1), k=1,)[1][0][0]
        return closest_centroid_ids

    def _get_closest_centroid_ids(self, kdtree, coordinates, centroids):
        closest_centroid_ids = kdtree.query(
            coordinates.reshape(1, -1), k=len(centroids),
        )[1][0]
        return closest_centroid_ids

    def _get_distance_to_closest_centroid(self, kdtree, coordinates):
        distance = kdtree.query(coordinates.reshape(1, -1), k=1,)[0][0][0]
        return distance

    def _get_furthest_super_areas(self, domain_centroids, kdtree_centroids):
        super_areas_per_domain = len(self.super_area_names) / self.number_of_domains
        kdtree_centroids = self._initialise_kdtree(domain_centroids)
        # sort super areas by further away from closest to any cluster
        _distances = []
        for super_area in self.super_area_names:
            _distances.append(
                self._get_distance_to_closest_centroid(
                    kdtree_centroids,
                    self.super_area_centroids.loc[super_area, ["X", "Y"]].values,
                )
            )
        sorted_idx = np.argsort(_distances)[::-1]
        super_area_names = np.array(self.super_area_names)[sorted_idx]
        return super_area_names

    def assign_super_areas_to_centroids(self, domain_centroids):
        kdtree_centroids = self._initialise_kdtree(domain_centroids)
        score_per_domain = {
            centroid_id: 0 for centroid_id in range(len(domain_centroids))
        }
        super_areas_per_domain = {
            centroid_id: [] for centroid_id in range(len(domain_centroids))
        }
        total = 0
        flagged = np.zeros(len(self.super_area_names))
        for tolerance in [0.0, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, np.inf]:
            for i, super_area_name in enumerate(self.super_areas_sorted):
                if flagged[i]:
                    continue
                super_area_score = self.score_per_super_area[super_area_name]
                closest_centroid_ids = self._get_closest_centroid_ids(
                    kdtree_centroids,
                    self.super_area_centroids.loc[super_area_name, ["X", "Y"]].values,
                    domain_centroids,
                )
                for centroid_id in closest_centroid_ids:
                    if score_per_domain[centroid_id] < self.average_score_per_domain * (
                        1 + tolerance
                    ):
                        score_per_domain[centroid_id] += super_area_score
                        super_areas_per_domain[centroid_id].append(super_area_name)
                        total += 1
                        flagged[i] = 1
                        break
        assert total == len(self.super_area_names)
        return super_areas_per_domain

    def compute_domain_centroids(self, super_areas_per_domain):
        centroids = []
        for domain, super_area_names in super_areas_per_domain.items():
            super_area_centroids = self.super_area_centroids.loc[
                super_area_names, ["X", "Y"]
            ].values
            centroid = np.mean(super_area_centroids, axis=0)
            centroids.append(centroid)
        return np.array(centroids)

    def _domain_split_iteration(self, domain_centroids):
        super_areas_per_domain = self.assign_super_areas_to_centroids(domain_centroids)
        domain_centroids = self.compute_domain_centroids(super_areas_per_domain)
        return domain_centroids

    def iterate_domain_split(self, domain_centroids, niter=20):
        # first make an initial guess with KMeans.
        for i in range(niter):
            if i % 5 == 0:
                logger.info(f"Domain splitter -- iteration {i+1} of {niter}")
            domain_centroids = self._domain_split_iteration(domain_centroids)
        return domain_centroids

    def generate_split_from_centroids(self, domain_centroids):
        # assign each to closest
        super_areas_per_domain = {
            centroid_id: [] for centroid_id in range(len(domain_centroids))
        }
        kdtree_centroids = self._initialise_kdtree(domain_centroids)
        for super_area_name in self.super_area_names:
            closest_centroid_id = self._get_closest_centroid_id(
                kdtree_centroids,
                self.super_area_centroids.loc[super_area_name, ["X", "Y"]].values,
            )
            super_areas_per_domain[closest_centroid_id].append(super_area_name)
        return super_areas_per_domain

    def generate_domain_split(self, niter=20):
        initial_centroids = self._get_kmeans_centroids()
        domain_centroids = self.iterate_domain_split(initial_centroids, niter=niter)
        super_areas_per_domain = self.generate_split_from_centroids(domain_centroids)
        return super_areas_per_domain
