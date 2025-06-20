# june/mpi_wrapper.py
import os
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger("mpi_wrapper")

# Try to import MPI, but don't fail if it's not available
try:
    from mpi4py import MPI as RealMPI
    mpi_available = True
    mpi_comm = RealMPI.COMM_WORLD
    mpi_rank = mpi_comm.Get_rank()
    mpi_size = mpi_comm.Get_size()
    print(f"MPI available with {mpi_size} processes")
    
    # Re-export the real MPI constants
    MPI = RealMPI
    MPI_UINT32_T = RealMPI.UINT32_T
    
except ImportError:
    print("MPI not available, running in single-process mode")
    mpi_available = False
    
    # Define fallback classes and constants
    class DummyMPI:
        """
        Dummy MPI implementation for single-process mode.
        """
        # Define constants that would normally come from MPI
        UINT32_T = 'UINT32_T'  # Just a placeholder
        ANY_SOURCE = -1
        
        class Status:
            def __init__(self):
                pass
                
            def Get_source(self):
                return 0
        
        class COMM_WORLD:
            @staticmethod
            def Get_rank():
                return 0
                
            @staticmethod
            def Get_size():
                return 1
                
            @staticmethod
            def Barrier():
                # No-op in single process mode
                pass
                
            @staticmethod
            def bcast(obj, root=0):
                return obj
                
            @staticmethod
            def allgather(obj):
                return [obj]
                
            @staticmethod
            def alltoall(obj):
                # Return same length array
                return [0] * len(obj) if isinstance(obj, (list, tuple, np.ndarray)) else [0]
                
            @staticmethod
            def Alltoallv(sendbuf, recvbuf):
                # In single process mode, this is a no-op
                # We would normally just return the buffer, but we need to handle
                # the complex MPI parameters
                return recvbuf
                
            @staticmethod
            def iprobe(source=0, tag=0, status=None):
                # Always return no messages in non-MPI mode
                return False
                
            @staticmethod
            def send(obj, dest=0, tag=0):
                # No-op in single process mode
                pass
                
            @staticmethod
            def recv(source=0, tag=0):
                # Return None in single process mode
                return None
    
    # Create the dummy objects
    MPI = DummyMPI()
    MPI_UINT32_T = MPI.UINT32_T
    mpi_comm = MPI.COMM_WORLD
    mpi_rank = 0
    mpi_size = 1


class MovablePeople:
    """
    Class for managing mobile people across domains.
    This version is MPI-aware but works in both MPI and non-MPI modes.
    """
    def __init__(self):
        self.skinny_out = {}
        self.skinny_in = {}
        self.index = {}

    def count_total_people(self):
        """
        Calculate the total number of people in skinny_out across all domains.
        
        Returns
        -------
        int
            Total number of people scheduled for transfer
        """
        total_count = 0
        for domain_id in self.skinny_out:
            for group_spec in self.skinny_out[domain_id]:
                for group_id in self.skinny_out[domain_id][group_spec]:
                    for subgroup_type in self.skinny_out[domain_id][group_spec][group_id]:
                        total_count += len(self.skinny_out[domain_id][group_spec][group_id][subgroup_type])
        return total_count

    def count_people_by_domain(self):
        """
        Calculate the number of people going to each domain.
        
        Returns
        -------
        dict
            Dictionary mapping domain_id to number of people
        """
        counts_by_domain = {}
        for domain_id in self.skinny_out:
            domain_count = 0
            for group_spec in self.skinny_out[domain_id]:
                for group_id in self.skinny_out[domain_id][group_spec]:
                    for subgroup_type in self.skinny_out[domain_id][group_spec][group_id]:
                        domain_count += len(self.skinny_out[domain_id][group_spec][group_id][subgroup_type])
            counts_by_domain[domain_id] = domain_count
        return counts_by_domain

    def add_person(self, person, external_subgroup):
        """Add or update a person to the outward facing group"""
        domain_id = external_subgroup.domain_id
        
        # Rest of implementation only matters in MPI mode
        if not mpi_available and domain_id != 0:
            return  # In non-MPI mode, we only care about domain 0
            
        group_spec = external_subgroup.spec
        group_id = external_subgroup.group_id
        subgroup_type = external_subgroup.subgroup_type

        # Initialize domain structures if needed
        if domain_id not in self.skinny_out:
            self.skinny_out[domain_id] = {}
        if group_spec not in self.skinny_out[domain_id]:
            self.skinny_out[domain_id][group_spec] = {}
        if group_id not in self.skinny_out[domain_id][group_spec]:
            self.skinny_out[domain_id][group_spec][group_id] = {}
        if subgroup_type not in self.skinny_out[domain_id][group_spec][group_id]:
            self.skinny_out[domain_id][group_spec][group_id][subgroup_type] = {}

        # Create the view array with person data
        if person.infected:
            view = [
                person.id,
                person.infection.transmission.probability,
                person.infection.infection_id(),
                False,
                np.array([], dtype=np.int64),
                np.array([], dtype=np.float64),
                mpi_rank,
                True,
            ]
        else:
            susceptibility_inf_ids, susceptibility_inf_suscs = person.immunity.serialize()
            view = [
                person.id,
                0.0,
                0,
                True,
                np.array(susceptibility_inf_ids, dtype=np.int64),
                np.array(susceptibility_inf_suscs, dtype=np.float64),
                mpi_rank,
                True,
            ]

        self.skinny_out[domain_id][group_spec][group_id][subgroup_type][person.id] = view

    def delete_person(self, person, external_subgroup):
        """Remove a person from the external subgroup"""
        domain_id = external_subgroup.domain_id
        
        if not mpi_available and domain_id != 0:
            return 0  # In non-MPI mode, success by default
            
        group_spec = external_subgroup.spec
        group_id = external_subgroup.group_id
        subgroup_type = external_subgroup.subgroup_type
        
        try:
            # Remove from skinny_out
            del self.skinny_out[domain_id][group_spec][group_id][subgroup_type][person.id]
            return 0
        except KeyError:
            return 1

    def serialise(self, rank):
        """Serialize person data for MPI communication"""
        # In single-process mode, this is simplified
        if not mpi_available:
            return None, None, 0
            
        keys, data = [], []
        if rank not in self.skinny_out:
            return None, None, 0

        # Serialize person data
        for group_spec in self.skinny_out[rank]:
            for group_id in self.skinny_out[rank][group_spec]:
                for subgroup_type in self.skinny_out[rank][group_spec][group_id]:
                    keys.append((
                        group_spec,
                        group_id,
                        subgroup_type,
                        len(self.skinny_out[rank][group_spec][group_id][subgroup_type])
                    ))
                    data += [
                        view
                        for pid, view in self.skinny_out[rank][group_spec][group_id][
                            subgroup_type
                        ].items()
                    ]

        outbound = np.array(data, dtype=object)
        
        return keys, outbound, outbound.shape[0]

    def update(self, rank, keys, rank_data):
        """Update with person registration in the destination rank"""
        # In single-process mode, this is simplified
        if not mpi_available:
            return
            
        index = 0

        for key in keys:
            group_spec, group_id, subgroup_type, n_data = key
            if group_spec not in self.skinny_in:
                self.skinny_in[group_spec] = {}
            if group_id not in self.skinny_in[group_spec]:
                self.skinny_in[group_spec][group_id] = {}
            if subgroup_type not in self.skinny_in[group_spec][group_id]:
                self.skinny_in[group_spec][group_id][subgroup_type] = {}
            
            data = rank_data[index : index + n_data]
            index += n_data

            try:
                # Update skinny_in with person data
                for k, i, t, s, iids, iis, d, a in data:
                    person_id = int(k)
                    # Register person in Person._persons dictionary
                    from june.demography import Person
                    if person_id not in Person._persons:
                        # Create minimal person instance
                        person = Person(
                            id=person_id,
                        )
                        person._home_rank = d
                        person._current_rank = mpi_rank
                        # This will automatically register in Person._persons
                    else:
                        person = Person._persons[person_id]
                        # Update person's rank since they've moved
                        person._current_rank = mpi_rank
                    
                    self.skinny_in[group_spec][group_id][subgroup_type][person_id] = {
                        "inf_prob": i,
                        "inf_id": t,
                        "susc": s,
                        "immunity_inf_ids": iids,
                        "immunity_suscs": iis,
                        "dom": d,
                        "active": a,
                    }
            except Exception:
                print("failing", rank, "f-done")
                raise


def move_info(info2move):
    """
    Move information between processes in MPI mode, or simply return the 
    information as-is in non-MPI mode.
    
    Parameters
    ----------
    info2move : list
        Information to move between processes
        
    Returns
    -------
    tuple
        (buffer, n_sending, n_receiving)
    """
    if not mpi_available:
        # In non-MPI mode, just flatten the list and return it
        buffer = np.concatenate(info2move)
        return buffer, len(buffer), len(buffer)
        
    # In MPI mode, do the actual movement
    assert len(info2move) == mpi_size
    buffer = np.concatenate(info2move)
    assert buffer.dtype == np.uint32

    n_sending = len(buffer)
    count = np.array([len(x) for x in info2move])
    displ = np.array([sum(count[:p]) for p in range(len(info2move))])

    values = mpi_comm.alltoall(count)
    n_receiving = sum(values)
    r_buffer = np.zeros(n_receiving, dtype=np.uint32)
    rdisp = np.array([sum(values[:p]) for p in range(len(values))])

    mpi_comm.Alltoallv(
        [buffer, count, displ, MPI.UINT32_T],
        [r_buffer, values, rdisp, MPI.UINT32_T]
    )

    return r_buffer, n_sending, n_receiving
