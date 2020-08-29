from typing import List
from itertools import chain

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

    def __init__(self):
        pass

    def __iter__(self):
        return iter(self.super_areas)

class Domains:
    def __init__(self, domains: List[Domain]):
        self.domains = domains

    @classmethod
    def from_hdf5(self, domain_super_area_names, hdf5_file_path: str):
        return generate_domain_from_hdf5(domain_super_area_names, hdf5_file_path)



