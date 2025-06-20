# june/domains/domain.py
from itertools import count
from june.global_context import GlobalContext
from june.hdf5_savers import generate_domain_from_hdf5

# Import from wrapper instead of directly
from june.mpi_wrapper import MovablePeople, mpi_available

class Domain:
    """
    The idea is that the world is divided in domains, which are just collections of super areas with
    people living/working/doing leisure in them.

    If we think as domains as sets, then world is the union of all domains, and each domain can have
    a non-zero intersection with other domains (some people can work and live in different domains).

    Domains are sent to MPI core to perform calculation, and communication between the processes is
    required to transfer the infection status of people.
    
    In non-MPI mode, there is only one domain containing all super areas.
    """

    _id = count()

    def __init__(self, id: int = None):
        if id is None:
            self.id = next(self._id)
        else:
            self.id = id
        self.movable_people = MovablePeople()  # Initialize MovablePeople for either mode

    def __iter__(self):
        return iter(self.super_areas)

    @classmethod
    def from_hdf5(
        cls,
        domain_id,
        super_areas_to_domain_dict: dict,
        hdf5_file_path: str,
        interaction_config: str = None,
    ):
        """
        Load a domain from an HDF5 file.

        Parameters
        ----------
        domain_id : int
            The ID of the domain to load.
        super_areas_to_domain_dict : dict
            Mapping of super areas to domain IDs.
        hdf5_file_path : str
            Path to the HDF5 file.
        interaction_config : str
            Path to the interaction configuration file.

        Returns
        -------
        Domain
            The domain object loaded from the HDF5 file.
        """
        # Retrieve the global disease configuration
        disease_config = GlobalContext.get_disease_config()

        # Generate the domain
        domain = generate_domain_from_hdf5(
            domain_id=domain_id,
            super_areas_to_domain_dict=super_areas_to_domain_dict,
            file_path=hdf5_file_path,
            interaction_config=interaction_config
        )
        domain.id = domain_id
        return domain


