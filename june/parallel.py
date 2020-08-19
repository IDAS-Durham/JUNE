#
# Contains two methods to be monkey patched onto the World CLASS definition when we want a parallel world.
# Example usage in run_simulation.py:
#
#   ... load entire world from file as normal ...
#   # add parallelism
#   World.parallel_setup = parallel_setup
#   World.parallel_update = parallel_update
#   world.parallel_setup(world.super_areas[0:2])
#
import json
import numpy


def mydomain(super_areas, size):
    """ Generator to partition world into domains"""
    indices = numpy.arange(len(super_areas))
    splits = numpy.array_split(indices, size)
    for s in splits:
        yield super_areas[s[0]:s[-1]]

def parallel_setup(self, rank, size):
    """ Initialise by defining what part of the known world is outside _THIS_ domain."""

    # let's just brute force it with MPI for now
    # partition the list of superareas
    # each of the following lists is 2-d, first dimension is number of "other domains" of relevance,
    # second is workers in those domains.
    self.outside_workers = [[] for i in range(size)]
    self.inbound_workers = [[] for i in range(size)]
    self.domain_id = rank
    # need to find all the people who are in my domain who work elsewhere, and all those who live
    # elsewhere and work in my domain. All the other people can be deleted in this mpi process.
    # We could probably delete other parts of the world too, but we can do that in a later iteration.

    # Currently the person instances in world.people do not have the work_super_area populated when
    # read back from a file so we have to work this all out from the people in the areas.

    # First partition information about superareas
    self.parallel_partitions = []
    for i, super_areas in enumerate(mydomain(self.super_areas, size)):
        self.parallel_partitions.append([sa.name for sa in super_areas])

    # Now parse people to see if they are in any of our interesting areas
    # Note that we can delete people who are not interesting!
    # We should probably delete other parts of the world that are not interesting too ...
    my_domain = self.parallel_partitions[rank]
    npeople = self.people.total_people
    for person in self.people:
        home_super_area = person.area.super_area.name
        work_super_area = None
        if person.primary_activity.group.spec == "company":
            work_super_area = person.primary_activity.group.super_area.name
        if home_super_area in my_domain:
            if work_super_area and work_super_area != home_super_area:
                for i in self.parallel_partitions:
                    if i == rank:
                        continue  # we're interested in the others
                    if work_super_area in self.parallel_partitions[i]:
                        self.outside_workers[i].append(person)
                        break
        else:
            if work_super_area in my_domain:
                for i in self.parallel_partitions:
                    if i == rank:
                        continue
                    if home_super_area in self.parallel_partitions[i]:
                        self.inbound_workers[i].append(person)
                        break
            else:
                # this person is of no interest to this domain, they never spend any time here interacting
                # with anyone.
                del self.people[person]
                # (but do they exist somewhere else)
    inbound = sum([len(i) for i in self.inbound_workers])
    outbound = sum([len(i) or i in self.outside_workers])
    print(f'Partition {rank} has {self.people.total_people}(of {npeople} - {inbound} in and {outbound} out).')



















def parallel_update(self, direction, timestep):
    """
    (This method overrides the superclass mixin stub)

    The world can contain two or more domains, each of which is operating in parallel.

    To make this work for this domain , we need to mark some people as outside when they do not need to be processed
    since they have crossed into another domain (gone to work in another domain or returned
    to another domain having worked in this domain).
    :param world:
    :param direction: 'am' or 'pm'
    :return: updated world.

    When
        direction='am': people from outside come in to work or people inside leave to work,
        direction='pm': people return from work or head home to another domain.
    """

    # Note that we have to put people before getting people, otherwise we get a deadlock
    if direction == 'am':
        # send people away
        # we need only to pass infection status of infected people, so only some of these folk need writing out
        for id, outside_domain in enumerate(self.outside_workers):
            tell_them = []
            for person in outside_domain:
                if not person.hospitalised:
                    person.busy = True
                #FIXME: Actually, this is the wrnog place, since policy may keep them at home ...
                if person.infected:
                    tell_them.append(person)
            _put_updates(self, id, tell_them, timestep)
        # pay attention to people who are coming in
        for id, outside_domain in enumerate(self.inbound_workers):
            for person in outside_domain:
                person.busy = False
            # we might need to update the infection status of these people
            _get_updates(self, id, timestep)
    elif direction == 'pm':

        # FIXME: What happens to inbound workers during initialisation?
        for id, outside_domain in enumerate(self.inbound_workers):
            tell_them = []
            for person in self.inbound_workers:
                person.busy = True
                if person.infected: # it happened at work!
                    tell_them.append(person)
            _put_updates(self, id, tell_them, timestep)
        # now see if any of our workers outside have got infected.
        for id, outside_domain in enumerate(self.outside_workers):
            _get_updates(self, id, timestep)


def _put_updates(self, domain_id, tell_them, timestep):
    """
    Write necessary information about people for infection transmission while they are outside.
    In practice, we only need to tell them about infected people (the list of people called "tell_them").
    """
    # my domain is self.domain_id, and we are sending to domain_id
    data = [set_person_info(p) for p in tell_them]
    # at this point, we do a send/receive in MPI land.
    # after receive would need to do the inverse of set_person_info ...
    #with open(f'parallel_putter_{self.domain_id}_{domain_id}_{timestep}.json','w') as f:
    #    json.dump(data, f)
    print(f"Serialisation of person infection properties for parallelisation is not yet working")
    #forget all this gubbins, let's use MPI!

def _get_updates(self, domain_id, timestep):
    """" Get necessary information about possible changes which happened to people while outside"""
    #try:
    #    for id in self.other_domain_ids:
    #        with open(f'parallel_putter_{id}_{timestep}.json','r') as f:
    #            updated = json.load(f)
    #except FileNotFoundError:
    #    # We'd wait a fraction of a second here in real life, but for now, we'll just skip it
    #    # FIXME
    #    pass
    # forget all this gubbins, let's use MPI.

    #FIXME: Are people indexed in anyway? Then use that index here ...
    print(f"Unable (yet) to update people from domain {id} for timestep {timestep}")


def set_person_info(person):
    """ set person info that needs to be passed and serialise it"""
    return int(person.id)










