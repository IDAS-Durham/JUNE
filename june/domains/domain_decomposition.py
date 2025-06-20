# june/domains/domain_decomposition.py
import logging
import json
import pandas as pd
import numpy as np
from score_clustering import Point, ScoreClustering

from june import paths
from june.hdf5_savers import load_data_for_domain_decomposition
from june.mpi_wrapper import mpi_available, mpi_size

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
    
    In non-MPI mode or with a single MPI process, all super areas are assigned to domain 0.
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
        
        # In non-MPI mode or single process, create a simple split
        if not mpi_available or number_of_domains <= 1:
            self.simple_split = True
            self.super_area_data = super_area_data
            return
            
        self.simple_split = False
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
        
        # If not using MPI or only one domain is needed, create a simple split
        if not mpi_available or number_of_domains <= 1:
            # Assign all super areas to domain 0
            super_areas_per_domain = {0: list(super_area_data.keys())}
            
            # Calculate total score for domain 0
            total_score = sum(
                weights["population"] * data["n_people"]
                + weights["workers"] * (data["n_workers"] + data["n_pupils"])
                + weights["commuters"] * data["n_commuters"]
                for data in super_area_data.values()
            )
            score_per_domain = {0: total_score}
            
            return super_areas_per_domain, score_per_domain
        
        # Otherwise, use the normal clustering approach
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
        # For single-domain case
        if self.simple_split:
            super_areas_per_domain = {0: list(self.super_area_data.keys())}
            
            # Calculate total score for domain 0
            total_score = sum(
                default_weights["population"] * data["n_people"]
                + default_weights["workers"] * (data["n_workers"] + data["n_pupils"])
                + default_weights["commuters"] * data["n_commuters"]
                for data in self.super_area_data.values()
            )
            score_per_domain = {0: total_score}
            
            return super_areas_per_domain, score_per_domain
        
        # For multi-domain case
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