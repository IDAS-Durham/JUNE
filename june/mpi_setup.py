from mpi4py import MPI
from june.groups import ExternalSubgroup
import numpy as np
from june.exc import SimulatorError

mpi_comm = MPI.COMM_WORLD
mpi_rank = mpi_comm.Get_rank()
mpi_size = mpi_comm.Get_size()

def add_person_entry_old(to_send_abroad, person, external_subgroup: ExternalSubgroup):
    domain_id = external_subgroup.domain_id
    group_spec = external_subgroup.group_spec
    group_id = external_subgroup.group_id
    subgroup_type = external_subgroup.subgroup_type
    if domain_id not in to_send_abroad:
        to_send_abroad[domain_id] = {}  # allocate domain id
    if group_spec not in to_send_abroad[domain_id]:
        to_send_abroad[domain_id][group_spec] = {}
    if group_id not in to_send_abroad[domain_id][group_spec]:
        to_send_abroad[domain_id][group_spec][group_id] = {}
    if subgroup_type not in to_send_abroad[domain_id][group_spec][group_id]:
        to_send_abroad[domain_id][group_spec][group_id][subgroup_type] = {}
    if person.infected:
        to_send_abroad[domain_id][group_spec][group_id][subgroup_type][person.id] = {
            "inf_prob": person.infection.transmission.probability,
            "susc": 0.0,
            "dom": mpi_rank,
        }
    else:
        to_send_abroad[domain_id][group_spec][group_id][subgroup_type][person.id] = {
            "inf_prob": 0.0,
            "susc": person.susceptibility,
            "dom": mpi_rank,
        }


class MovablePeople:
    """
    Holds information about people who might be present in a domain, but may or may not be be,
    given circumstances. They have skinny profiles, which only have their id, infection probability,
    susceptibility, home domain, and whether active or not. For now, we mimic the original structure,
    but with an additional interface.
    """
    def __init__(self):
        self.skinny_out = {}
        self.skinny_in = {}
        self.index = {}

    def add_person(self, person, external_subgroup):
        """ Add or update a person to the outward facing group """
        domain_id = external_subgroup.domain_id
        group_spec = external_subgroup.group_spec
        group_id = external_subgroup.group_id
        subgroup_type = external_subgroup.subgroup_type

        if domain_id not in self.skinny_out:
            self.skinny_out[domain_id] = {}  # allocate domain id
        if group_spec not in self.skinny_out[domain_id]:
            self.skinny_out[domain_id][group_spec] = {}
        if group_id not in self.skinny_out[domain_id][group_spec]:
            self.skinny_out[domain_id][group_spec][group_id] = {}
        if subgroup_type not in self.skinny_out[domain_id][group_spec][group_id]:
            self.skinny_out[domain_id][group_spec][group_id][subgroup_type] = {}

        if person.infected:
            view = [person.id, person.infection.transmission.probability, 0.0, mpi_rank, True]
        else:
            view = [person.id, 0.0, person.susceptibility, mpi_rank, True]

        self.skinny_out[domain_id][group_spec][group_id][subgroup_type][person.id] = view

    def delete_person(self, person, external_subgroup):
        """ Remove a person from the external subgroup. For now we actually do it. Later
        we may flag them. """
        domain_id = external_subgroup.domain_id
        group_spec = external_subgroup.group_spec
        group_id = external_subgroup.group_id
        subgroup_type = external_subgroup.subgroup_type
        try:
            del self.skinny_out[domain_id][group_spec][group_id][subgroup_type][person.id]
            return 0
        except KeyError:
            return 1

    def serialise(self, rank):
        """ Hopefully more efficient than standard pickle"""
        keys, data = [], []
        if rank not in self.skinny_out:
            return None, None, 0
        for group_spec in self.skinny_out[rank]:
            for group_id in self.skinny_out[rank][group_spec]:
                for subgroup_type in self.skinny_out[rank][group_spec][group_id]:
                    keys.append((group_spec, group_id, subgroup_type,
                                 len(self.skinny_out[rank][group_spec][group_id][subgroup_type])))
                    data += [view for pid, view in
                             self.skinny_out[rank][group_spec][group_id][subgroup_type].items()]
        outbound = np.array(data)
        return keys, outbound, outbound.shape[0]

    def update(self, rank, keys, rank_data):
        """ Update the information we have about people coming into our domain
        :param rank: domain of origin
        :param keys: dictionary keys for the group structure
        :param rank_data: numpy array of all the person data
        """
        index = 0

        for key in keys:
            group_spec, group_id, subgroup_type, n_data = key
            if group_spec not in self.skinny_in:
                self.skinny_in[group_spec] = {}
            if group_id not in self.skinny_in[group_spec]:
                self.skinny_in[group_spec][group_id] = {}
            if subgroup_type not in self.skinny_in[group_spec][group_id]:
                self.skinny_in[group_spec][group_id][subgroup_type] = {}
            data = rank_data[index:index+n_data]
            index += n_data

            try:
                self.skinny_in[group_spec][group_id][subgroup_type].update({
                    int(k):  {"inf_prob": i, "susc": s, "dom": d, "active":a} for k,i,s,d,a in data})
            except:
                print('failing', rank, 'f-done')
                raise







