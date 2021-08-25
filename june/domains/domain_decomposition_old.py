import numpy as np
import pandas as pd
import logging
import h5py
from sklearn.cluster import KMeans
from sklearn.neighbors import KDTree
from typing import List
from collections import defaultdict

from june.geography import SuperArea
from june.hdf5_savers import load_data_for_domain_decomposition
from june import paths

default_super_area_centroids = (
    paths.data_path / "input/geography/super_area_centroids.csv"
)

logger = logging.getLogger("domain")

default_weights = {"population" : 1, "workers": 0.3, "commuters" : 0.3}

class DomainSplitterOld:
    """
    Class used to split the world into ``n`` domains containing an equal number
    of super areas continuous to each other.
    """

    def __init__(
        self,
        number_of_domains: int,
        super_area_data: dict,
        super_area_centroids: List[List[float]] = None,
        weights = default_weights,
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
        self.super_area_names = list(super_area_data.keys())
        self.number_of_domains = number_of_domains
        self.super_area_centroids = super_area_centroids
        if self.super_area_centroids is None:
            self.super_area_centroids = pd.read_csv(
                default_super_area_centroids, index_col=0
            )
        if self.super_area_names is None:
            self.super_area_names = self.super_area_centroids.index.values
        self.super_area_centroids = self.super_area_centroids.loc[self.super_area_names]
        self.score_per_super_area = self.get_scores_per_super_area(super_area_data, weights=weights)
        self.average_score_per_domain = (
            sum(self.score_per_super_area.values()) / number_of_domains
        )
        self.super_areas_sorted = self._sort_super_areas_by_score()

    @classmethod
    def generate_world_split(
        cls,
        number_of_domains: int,
        world_path: str,
        super_area_centroids: List[List[float]] = None,
        niter=20,
    ):
        super_area_data = load_data_for_domain_decomposition(world_path)
        ds = cls(
            number_of_domains=number_of_domains,
            super_area_data=super_area_data,
            super_area_centroids=super_area_centroids,
        )
        return ds.generate_domain_split(niter=niter)

    def get_scores_per_super_area(
        self,
        super_area_data:dict,
        weights: dict,
    ):
        """
        Calculates the score per super area
        The score is calculated as:
        score = population_weight * n_people + 
            workers_pupils_weight * (n_workers + n_pupils) + commute_weight * n_commuters

        Parameters
        ----------
        super_area_data
            dictionary with the super area names as keys and as values the number of people, 
            workers, pupils, and commuters per super area.
        """
        workers_pupils_weight = 1
        commute_weight = 2
        ret = defaultdict(float)
        for super_area, data in super_area_data.items():
            ret[super_area] = (
                weights["population"] * data["n_people"]
                + weights["workers"] * (data["n_workers"] + data["n_pupils"])
                + weights["commuters"] * data["n_commuters"]
            )
        return ret

    def _sort_super_areas_by_score(self):
        """
        Sorts super areas by score
        """
        super_area_scores = [
            self.score_per_super_area[super_area]
            for super_area in self.super_area_names
        ]
        return [
            self.super_area_names[idx] for idx in np.argsort(super_area_scores)[::-1]
        ]

    def get_score_per_domain(self, super_areas_per_domain):
        """
        Returns a dict mapping domain -> score, where score is the sum of the scores
        of all super areas in the domain.
        """
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
        closest_centroid_ids = kdtree.query(coordinates.reshape(1, -1), k=1,)[1][
            0
        ][0]
        return closest_centroid_ids

    def _get_closest_centroid_ids(self, kdtree, coordinates, centroids):
        closest_centroid_ids = kdtree.query(
            coordinates.reshape(1, -1),
            k=len(centroids),
        )[1][0]
        return closest_centroid_ids

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

    def _domain_split_iteration(self, super_areas_per_domain):
        domain_centroids = self.compute_domain_centroids(super_areas_per_domain)
        return domain_centroids

    def compute_decomposition_unbalance(self, super_areas_per_domain):
        scores_per_domain = self.get_score_per_domain(super_areas_per_domain)
        return max(scores_per_domain.values()) / min(scores_per_domain.values())

    def iterate_domain_split(self, domain_centroids, niter=20):
        """
        Iterates the splitting of domains
        """
        # first make an initial guess with KMeans.
        best_candidate_score = np.inf
        best_centroids = None
        for i in range(niter):
            if i % 5 == 0:
                logger.info(f"Domain splitter -- iteration {i+1} of {niter}")
            super_areas_per_domain = self.assign_super_areas_to_centroids(
                domain_centroids
            )
            domain_centroids = self._domain_split_iteration(super_areas_per_domain)
            unbalance_score = self.compute_decomposition_unbalance(
                super_areas_per_domain
            )
            if unbalance_score < best_candidate_score:
                best_candidate_score = unbalance_score
                best_centroids = domain_centroids
        logger.info(f"Best split candidate has a score of {best_candidate_score:.2f}")
        return best_centroids

    def generate_split_from_centroids(self, domain_centroids):
        """
        Given domain centroids, assigns each super area to the closest centroid,
        generating a tesselation of the world.
        """
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
        """
        Main function of this class, generates a domain split using ``niter`` iterations.
        """
        initial_centroids = self._get_kmeans_centroids()
        domain_centroids = self.iterate_domain_split(initial_centroids, niter=niter)
        super_areas_per_domain = self.generate_split_from_centroids(domain_centroids)
        return super_areas_per_domain
