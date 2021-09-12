import logging
import json
import pandas as pd
import numpy as np
from typing import List
from score_clustering import Point, ScoreClustering

from june import paths
from june.hdf5_savers import load_data_for_domain_decomposition

default_super_area_adjaceny_graph_path = (
    paths.data_path / "input/geography/super_area_adjacency_graph.json"
)
default_super_area_centroids_path = (
    paths.data_path / "input/geography/super_area_centroids.csv"
)


logger = logging.getLogger("domain")

default_weights = {"population": 5.0, "workers": 1.0, "commuters": 1.0}


class DomainSplitter:
    """
    Class used to split the world into ``n`` domains containing an equal number
    of super areas continuous to each other.
    """

    def __init__(
        self,
        number_of_domains: int,
        super_area_data: dict,
        super_area_centroids_path: str = default_super_area_centroids_path,
        super_area_adjacency_graph_path: str = default_super_area_adjaceny_graph_path,
        weights=default_weights,
    ):
        """
        Parameters
        ----------
        number_of_domains
            how many domains to split for
        super_area_data
            dictionary specifying the number of people, workers, pupils and commmuters
            per super area
        """
        self.number_of_domains = number_of_domains
        with open(super_area_adjacency_graph_path, "r") as f:
            self.adjacency_graph = json.load(f)
        self.super_area_data = super_area_data
        self.super_area_df = pd.read_csv(super_area_centroids_path, index_col=0)
        self.super_area_df = self.super_area_df.loc[super_area_data.keys()]
        super_area_scores = list(
            map(lambda x: self.get_score(x, weights=weights), self.super_area_df.index)
        )
        self.super_area_df.loc[:, "score"] = super_area_scores

    @classmethod
    def generate_world_split(
        cls,
        number_of_domains: int,
        world_path: str,
        weights=default_weights,
        super_area_centroids_path: str = default_super_area_centroids_path,
        super_area_adjacency_graph_path: str = default_super_area_adjaceny_graph_path,
        maxiter=100,
    ):
        super_area_data = load_data_for_domain_decomposition(world_path)
        ds = cls(
            number_of_domains=number_of_domains,
            super_area_data=super_area_data,
            super_area_centroids_path=super_area_centroids_path,
            super_area_adjacency_graph_path=super_area_adjacency_graph_path,
            weights=weights,
        )
        return ds.generate_domain_split(maxiter=maxiter)

    def get_score(self, super_area, weights=default_weights):
        data = self.super_area_data[super_area]
        return (
            weights["population"] * data["n_people"]
            + weights["workers"] * (data["n_workers"] + data["n_pupils"])
            + weights["commuters"] * data["n_commuters"]
        )

    def generate_domain_split(self, maxiter=100):
        points = list(
            self.super_area_df.apply(
                lambda row: Point(row["X"], row["Y"], row["score"], row.name), axis=1
            ).values
        )
        for point in points:
            point.neighbors = [
                points[i]
                for i in np.where(self.adjacency_graph[point.name])[0]
                if i < len(points)
            ]
        sc = ScoreClustering(n_clusters=self.number_of_domains)
        clusters = sc.fit(points, maxiter=maxiter)
        super_areas_per_domain = {}
        score_per_domain = {}
        for (i, cluster) in enumerate(clusters):
            super_areas_per_domain[i] = [point.name for point in cluster.points]
            score_per_domain[i] = cluster.score
        print(f"Score is {sc.calculate_score_unbalance(clusters)}")
        return super_areas_per_domain, score_per_domain
