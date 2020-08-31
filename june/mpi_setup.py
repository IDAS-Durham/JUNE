from mpi4py import MPI
from june.groups import ExternalSubgroup

mpi_comm = MPI.COMM_WORLD
mpi_rank = mpi_comm.Get_rank()
mpi_size = mpi_comm.Get_size()

def count_people_in_dict(people_from_abroad_dict):
    ret = 0
    for group_spec in people_from_abroad_dict:
        for group_id in people_from_abroad_dict[group_spec]:
            for subgroup_type in people_from_abroad_dict[group_spec][group_id]:
                ret += len(people_from_abroad_dict[group_spec][group_id][subgroup_type])
    return ret


def update_data(people_from_abroad, data):
    for group_spec in data:
        if group_spec not in people_from_abroad:
            people_from_abroad[group_spec] = {}
        for group_id in data[group_spec]:
            if group_id not in people_from_abroad[group_spec]:
                people_from_abroad[group_spec][group_id] = {}
            for subgroup_type in data[group_spec][group_id]:
                if subgroup_type not in people_from_abroad[group_spec][group_id]:
                    people_from_abroad[group_spec][group_id][subgroup_type] = {}
                for person_id, person_data in data[group_spec][group_id][
                    subgroup_type
                ].items():
                    people_from_abroad[group_spec][group_id][subgroup_type][
                        person_id
                    ] = person_data


def delete_person_entry(to_send_abroad, person, external_subgroup: ExternalSubgroup):
    try:
        del to_send_abroad[external_subgroup.domain_id][external_subgroup.group_spec][
            external_subgroup.group_id
        ][external_subgroup.subgroup_type][person.id]
        return 0
    except KeyError:
        return 1

def add_person_entry(to_send_abroad, person, external_subgroup: ExternalSubgroup):
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


