from typing import List
import numpy as np

from june.demography import Population
from june.demography.geography import SuperArea
from june.hdf5_savers import generate_domain_from_hdf5


class Domain:
    """
    The idea is that the world is divided in domains, which are just collections of super areas with
    people living/working/doing leisure in them.
    
    If we think as domains as sets, then world is the union of all domains, and each domain can have
    a non-zero intersection with other domains (some people can work and live in different domains).
    
    Domains are sent to MPI core to perfom calculation, and communcation between the processes is
    required to transfer the infection status of people.
    """

    def __init__(self, id: int = None):
        self.id = id

    @classmethod
    def _next_id(cls) -> int:
        """
        Iterate an id for this class. Each group class has its own id iterator
        starting at 0
        """
        return next(cls.__id_generators[cls])

    def __iter__(self):
        return iter(self.super_areas)

    @property
    def box_mode(self):
        return False

    @classmethod
    def from_hdf5(
        cls,
        domain_id,
        super_areas_to_domain_dict: dict,
        hdf5_file_path: str,
    ):
        domain = generate_domain_from_hdf5(
            domain_id = domain_id,
            super_areas_to_domain_dict=super_areas_to_domain_dict,
            file_path=hdf5_file_path,
        )
        domain.id = domain_id
        return domain

def generate_super_areas_to_domain_dict(number_of_super_areas, number_of_domains):
    ret = {}
    super_areas_per_domain = int(np.ceil(number_of_super_areas / number_of_domains))
    number_of_areas_per_domain = {}
    # guarantee that there is at least one are per domain
    for domain in range(number_of_domains):
        number_of_areas_per_domain[domain] = 1
    remaining = number_of_super_areas - number_of_domains
    for i in range(remaining):
        j = i % number_of_domains
        number_of_areas_per_domain[j] += 1
    domain_number = 0
    areas_per_domain = 0
    for super_area in range(number_of_super_areas):
        ret[super_area] = domain_number 
        areas_per_domain += 1
        if areas_per_domain == number_of_areas_per_domain[domain_number]:
            domain_number += 1
            areas_per_domain = 0
    return ret





