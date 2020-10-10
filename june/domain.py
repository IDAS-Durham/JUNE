import numpy as np
from typing import List
from itertools import count
from sklearn.cluster import KMeans
import geopandas as gpd

from june.demography import Population
from june.geography import SuperArea
from june.hdf5_savers import generate_domain_from_hdf5
from june import paths

default_super_area_shapes_path = paths.data_path / "plotting/super_area_boundaries"


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


#def generate_super_areas_to_domain_dict(
#    number_of_super_areas: int, number_of_domains: int
#):
#    """
#    Generates a dictionary mapping super_area ids ===> domain id.
#    We attempt to have the same number of super areas per domain,
#    and the super areas inside each domain have concurrent ids.
#    """
#    ret = {}
#    super_areas_per_domain = int(np.ceil(number_of_super_areas / number_of_domains))
#    number_of_areas_per_domain = {}
#    # guarantee that there is at least one are per domain
#    for domain in range(number_of_domains):
#        number_of_areas_per_domain[domain] = 1
#    remaining = number_of_super_areas - number_of_domains
#    for i in range(remaining):
#        j = i % number_of_domains
#        number_of_areas_per_domain[j] += 1
#    domain_number = 0
#    areas_per_domain = 0
#    for super_area in range(number_of_super_areas):
#        ret[super_area] = domain_number
#        areas_per_domain += 1
#        if areas_per_domain == number_of_areas_per_domain[domain_number]:
#            domain_number += 1
#            areas_per_domain = 0
#    return ret


def generate_domain_split(
    super_areas: List[str],
    number_of_domains: int,
    super_area_boundaries_path: str = default_super_area_shapes_path,
    super_area_key: str = "msoa11cd",
) -> dict:
    """
    Uses KMeans clustering algorithm to split a map of super areas into
    ``number_of_domains`` clusters. Returns a dict mapping each super area
    to the domain it belongs.

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
    super_area_shapes_df = gpd.read_file(super_area_boundaries_path)
    super_area_shapes_df = super_area_shapes_df.rename(
        columns={super_area_key: "super_area"}
    )
    super_area_shapes_df = super_area_shapes_df.loc[
        super_area_shapes_df["super_area"].isin(super_areas)
    ]
    centroids = super_area_shapes_df.geometry.centroid
    X = np.array(list(zip(centroids.x.values, centroids.y.values)))
    kmeans = KMeans(n_clusters=number_of_domains).fit(X)
    labels = kmeans.labels_
    super_area_shapes_df["labels"] = labels
    ret = super_area_shapes_df.loc[:,["super_area", "labels"]]
    ret.set_index("super_area", inplace=True)
    return ret.to_dict()['labels']
